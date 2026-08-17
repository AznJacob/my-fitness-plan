from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth.google import VerifiedGoogleIdentity
from app.auth.tokens import InvalidTokenError, generate_token, hash_token
from app.models import AuthenticationIdentity, User, UserSession
from app.security import (
    InvalidEmailError,
    InvalidPasswordError,
    hash_password,
    validate_and_normalize_email,
    verify_password,
)

_REGISTRATION_CONSTRAINTS = {
    "uq_authentication_identities_password_email",
    "uq_authentication_identities_provider_subject",
    "uq_users_normalized_email",
}
_IDENTITY_LINK_CONSTRAINTS = {
    "uq_authentication_identities_password_email",
    "uq_authentication_identities_provider_subject",
    "uq_authentication_identities_user_provider",
}
_GOOGLE_REAUTHENTICATION_MAX_AGE = timedelta(minutes=5)
_GOOGLE_REAUTHENTICATION_FUTURE_SKEW = timedelta(seconds=30)


class RegistrationConflictError(Exception):
    """Raised when registration cannot safely claim an account email."""


class InvalidCredentialsError(Exception):
    """Raised for all failed email/password authentication attempts."""


class AuthenticationRequiredError(Exception):
    """Raised when a request has no usable application session."""


class GoogleAccountConflictError(Exception):
    """Raised when a new Google identity cannot safely claim its email."""


class ReauthenticationFailedError(Exception):
    """Raised when fresh proof of the current account is absent or invalid."""


class IdentityAlreadyLinkedError(Exception):
    """Raised when the requested provider is already connected to the current user."""


class IdentityLinkConflictError(Exception):
    """Raised when an identity is owned by another user or cannot be linked safely."""


@dataclass(frozen=True, slots=True)
class IssuedSession:
    user: User
    session_token: str
    csrf_token: str
    expires_at: datetime


def _create_session(database_session: Session, user: User, lifetime_seconds: int) -> IssuedSession:
    session_token = generate_token()
    csrf_token = generate_token()
    expires_at = datetime.now(UTC) + timedelta(seconds=lifetime_seconds)
    database_session.add(
        UserSession(
            user=user,
            token_hash=hash_token(session_token),
            csrf_token_hash=hash_token(csrf_token),
            expires_at=expires_at,
        )
    )
    return IssuedSession(
        user=user,
        session_token=session_token,
        csrf_token=csrf_token,
        expires_at=expires_at,
    )


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(error.orig, "diag", None)
    return getattr(diagnostic, "constraint_name", None)


def _require_fresh_google_identity(google_identity: VerifiedGoogleIdentity) -> None:
    now = datetime.now(UTC)
    issued_at = datetime.fromtimestamp(google_identity.issued_at, UTC)
    if (
        issued_at < now - _GOOGLE_REAUTHENTICATION_MAX_AGE
        or issued_at > now + _GOOGLE_REAUTHENTICATION_FUTURE_SKEW
    ):
        raise ReauthenticationFailedError


def get_connected_methods(database_session: Session, user_id: UUID) -> set[str]:
    return set(
        database_session.scalars(
            select(AuthenticationIdentity.provider).where(AuthenticationIdentity.user_id == user_id)
        ).all()
    )


def link_google_identity(
    database_session: Session,
    user: User,
    password: str,
    google_identity: VerifiedGoogleIdentity,
) -> None:
    existing_methods = get_connected_methods(database_session, user.id)
    if "google" in existing_methods:
        raise IdentityAlreadyLinkedError

    password_identity = database_session.scalar(
        select(AuthenticationIdentity).where(
            AuthenticationIdentity.user_id == user.id,
            AuthenticationIdentity.provider == "password",
        )
    )
    verification = verify_password(
        password,
        password_identity.password_hash if password_identity else None,
    )
    if password_identity is None or not verification.valid:
        raise ReauthenticationFailedError

    _require_fresh_google_identity(google_identity)
    if google_identity.normalized_email != user.normalized_email:
        raise IdentityLinkConflictError
    owner_id = database_session.scalar(
        select(AuthenticationIdentity.user_id).where(
            AuthenticationIdentity.provider == "google",
            AuthenticationIdentity.provider_subject == google_identity.subject,
        )
    )
    if owner_id is not None:
        raise IdentityLinkConflictError

    if verification.updated_hash is not None:
        password_identity.password_hash = verification.updated_hash
    database_session.add(
        AuthenticationIdentity(
            user=user,
            provider="google",
            provider_subject=google_identity.subject,
            email=google_identity.email,
            normalized_email=google_identity.normalized_email,
            email_verified=True,
            password_hash=None,
        )
    )
    try:
        database_session.flush()
    except IntegrityError as error:
        if _constraint_name(error) in _IDENTITY_LINK_CONSTRAINTS:
            raise IdentityLinkConflictError from error
        raise


def link_password_identity(
    database_session: Session,
    user: User,
    new_password: str,
    google_identity: VerifiedGoogleIdentity,
) -> None:
    existing_methods = get_connected_methods(database_session, user.id)
    if "password" in existing_methods:
        raise IdentityAlreadyLinkedError

    _require_fresh_google_identity(google_identity)
    google_owner_id = database_session.scalar(
        select(AuthenticationIdentity.user_id).where(
            AuthenticationIdentity.provider == "google",
            AuthenticationIdentity.provider_subject == google_identity.subject,
        )
    )
    if google_owner_id != user.id:
        raise ReauthenticationFailedError

    database_session.add(
        AuthenticationIdentity(
            user=user,
            provider="password",
            provider_subject=user.normalized_email,
            email=user.normalized_email,
            normalized_email=user.normalized_email,
            email_verified=False,
            password_hash=hash_password(new_password),
        )
    )
    try:
        database_session.flush()
    except IntegrityError as error:
        if _constraint_name(error) in _IDENTITY_LINK_CONSTRAINTS:
            raise IdentityLinkConflictError from error
        raise


def register_user(
    database_session: Session,
    email_value: str,
    password: str,
    session_lifetime_seconds: int,
) -> IssuedSession:
    email = validate_and_normalize_email(email_value)

    existing_user_id = database_session.scalar(
        select(User.id).where(User.normalized_email == email.normalized)
    )
    if existing_user_id is not None:
        raise RegistrationConflictError

    user = User(normalized_email=email.normalized)
    identity = AuthenticationIdentity(
        user=user,
        provider="password",
        provider_subject=email.normalized,
        email=email.address,
        normalized_email=email.normalized,
        email_verified=False,
        password_hash=hash_password(password),
    )
    database_session.add_all((user, identity))
    issued_session = _create_session(database_session, user, session_lifetime_seconds)

    try:
        database_session.flush()
    except IntegrityError as error:
        if _constraint_name(error) in _REGISTRATION_CONSTRAINTS:
            raise RegistrationConflictError from error
        raise

    return issued_session


def login_user(
    database_session: Session,
    email_value: str,
    password: str,
    session_lifetime_seconds: int,
) -> IssuedSession:
    try:
        email = validate_and_normalize_email(email_value)
    except InvalidEmailError as error:
        verify_password(password, None)
        raise InvalidCredentialsError from error

    identity = database_session.scalar(
        select(AuthenticationIdentity)
        .options(joinedload(AuthenticationIdentity.user))
        .where(
            AuthenticationIdentity.provider == "password",
            AuthenticationIdentity.normalized_email == email.normalized,
        )
    )
    verification = verify_password(password, identity.password_hash if identity else None)
    if identity is None or not verification.valid:
        raise InvalidCredentialsError

    if verification.updated_hash is not None:
        identity.password_hash = verification.updated_hash

    issued_session = _create_session(database_session, identity.user, session_lifetime_seconds)
    database_session.flush()
    return issued_session


def sign_in_with_google(
    database_session: Session,
    google_identity: VerifiedGoogleIdentity,
    session_lifetime_seconds: int,
) -> IssuedSession:
    identity = database_session.scalar(
        select(AuthenticationIdentity)
        .options(joinedload(AuthenticationIdentity.user))
        .where(
            AuthenticationIdentity.provider == "google",
            AuthenticationIdentity.provider_subject == google_identity.subject,
        )
    )
    if identity is not None:
        issued_session = _create_session(
            database_session,
            identity.user,
            session_lifetime_seconds,
        )
        database_session.flush()
        return issued_session

    claimed_user_id = database_session.scalar(
        select(User.id).where(User.normalized_email == google_identity.normalized_email)
    )
    if claimed_user_id is not None:
        raise GoogleAccountConflictError

    user = User(normalized_email=google_identity.normalized_email)
    identity = AuthenticationIdentity(
        user=user,
        provider="google",
        provider_subject=google_identity.subject,
        email=google_identity.email,
        normalized_email=google_identity.normalized_email,
        email_verified=True,
        password_hash=None,
    )
    database_session.add_all((user, identity))
    issued_session = _create_session(database_session, user, session_lifetime_seconds)

    try:
        database_session.flush()
    except IntegrityError as error:
        if _constraint_name(error) in _REGISTRATION_CONSTRAINTS:
            raise GoogleAccountConflictError from error
        raise
    return issued_session


def get_authenticated_session(database_session: Session, raw_token: str | None) -> UserSession:
    if raw_token is None:
        raise AuthenticationRequiredError

    try:
        token_hash = hash_token(raw_token)
    except InvalidTokenError as error:
        raise AuthenticationRequiredError from error

    user_session = database_session.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user))
        .where(UserSession.token_hash == token_hash)
    )
    now = datetime.now(UTC)
    if (
        user_session is None
        or user_session.revoked_at is not None
        or user_session.expires_at <= now
    ):
        raise AuthenticationRequiredError
    return user_session


def revoke_session(user_session: UserSession) -> None:
    """Revoke a session that has already passed authentication and CSRF checks."""
    user_session.revoked_at = datetime.now(UTC)


__all__ = [
    "AuthenticationRequiredError",
    "GoogleAccountConflictError",
    "IdentityAlreadyLinkedError",
    "IdentityLinkConflictError",
    "InvalidCredentialsError",
    "InvalidEmailError",
    "InvalidPasswordError",
    "IssuedSession",
    "RegistrationConflictError",
    "ReauthenticationFailedError",
    "get_connected_methods",
    "get_authenticated_session",
    "login_user",
    "link_google_identity",
    "link_password_identity",
    "register_user",
    "revoke_session",
    "sign_in_with_google",
]
