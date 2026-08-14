import secrets
from typing import Annotated, Never

from fastapi import Cookie, Depends, Header, HTTPException, status

from app.auth.service import AuthenticationRequiredError, get_authenticated_session
from app.auth.tokens import InvalidTokenError, hash_token
from app.config import LOCAL_FRONTEND_ORIGINS
from app.database import DatabaseSession
from app.models import User, UserSession

SessionCookie = Annotated[str | None, Cookie(alias="mfp_session")]
CsrfCookie = Annotated[str | None, Cookie(alias="mfp_csrf")]
CsrfHeader = Annotated[str | None, Header(alias="X-CSRF-Token")]
OriginHeader = Annotated[str | None, Header(alias="Origin")]


def _reject_csrf() -> Never:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="CSRF validation failed.",
    )


def require_csrf_tokens(
    csrf_cookie: CsrfCookie = None,
    csrf_header: CsrfHeader = None,
    origin: OriginHeader = None,
) -> bytes:
    """Require an exact local origin and matching, well-formed double-submit tokens."""
    if origin not in LOCAL_FRONTEND_ORIGINS or csrf_cookie is None or csrf_header is None:
        _reject_csrf()

    try:
        cookie_hash = hash_token(csrf_cookie)
        header_hash = hash_token(csrf_header)
    except InvalidTokenError:
        _reject_csrf()

    if not secrets.compare_digest(cookie_hash, header_hash):
        _reject_csrf()
    return header_hash


def get_current_session(
    database_session: DatabaseSession,
    session_token: SessionCookie = None,
) -> UserSession:
    """Resolve the opaque cookie to one active database session."""
    try:
        return get_authenticated_session(database_session, session_token)
    except AuthenticationRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        ) from error


CurrentSession = Annotated[UserSession, Depends(get_current_session, scope="function")]


def get_current_user(current_session: CurrentSession) -> User:
    """Expose the application user established by the validated session."""
    return current_session.user


CurrentUser = Annotated[User, Depends(get_current_user, scope="function")]


def require_authenticated_csrf(
    current_session: CurrentSession,
    submitted_hash: Annotated[bytes, Depends(require_csrf_tokens)],
) -> UserSession:
    """Bind the double-submit CSRF token to the authenticated database session."""
    if not secrets.compare_digest(current_session.csrf_token_hash, submitted_hash):
        _reject_csrf()
    return current_session


AuthenticatedCsrfSession = Annotated[
    UserSession,
    Depends(require_authenticated_csrf, scope="function"),
]
