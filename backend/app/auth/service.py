from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

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


class RegistrationConflictError(Exception):
    """Raised when registration cannot safely claim an account email."""


class InvalidCredentialsError(Exception):
    """Raised for all failed email/password authentication attempts."""


class AuthenticationRequiredError(Exception):
    """Raised when a request has no usable application session."""


class GoogleAccountConflictError(Exception):
    """Raised when a new Google identity cannot safely claim its email."""


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
    "InvalidCredentialsError",
    "InvalidEmailError",
    "InvalidPasswordError",
    "IssuedSession",
    "RegistrationConflictError",
    "get_authenticated_session",
    "login_user",
    "register_user",
    "revoke_session",
    "sign_in_with_google",
]
