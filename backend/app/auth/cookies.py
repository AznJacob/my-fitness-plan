from datetime import UTC, datetime, timedelta

from fastapi import Response

from app.auth.service import IssuedSession
from app.config import Settings


def set_csrf_cookie(response: Response, token: str, settings: Settings) -> None:
    """Set the JavaScript-readable half of the double-submit CSRF defense."""
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.session_lifetime_seconds)
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        max_age=settings.session_lifetime_seconds,
        expires=expires_at,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite=settings.session_cookie_samesite,
    )


def set_authentication_cookies(
    response: Response,
    issued_session: IssuedSession,
    settings: Settings,
) -> None:
    """Set the opaque session cookie and JavaScript-readable CSRF cookie."""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=issued_session.session_token,
        max_age=settings.session_lifetime_seconds,
        expires=issued_session.expires_at,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )
    set_csrf_cookie(response, issued_session.csrf_token, settings)


def clear_authentication_cookies(response: Response, settings: Settings) -> None:
    """Expire both authentication cookies using the attributes that created them."""
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite=settings.session_cookie_samesite,
    )
