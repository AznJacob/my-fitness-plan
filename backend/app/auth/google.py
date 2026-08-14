from collections.abc import Callable
from dataclasses import dataclass
from time import time
from typing import Any, cast

from google.auth.exceptions import TransportError
from google.auth.transport.requests import Request
from google.oauth2 import id_token as google_id_token

from app.security import InvalidEmailError, validate_and_normalize_email

_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
google_token_verifier = cast(
    Callable[[str, Any, str], dict[str, Any]],
    google_id_token.verify_oauth2_token,
)


class InvalidGoogleTokenError(Exception):
    """Raised when Google credentials or required identity claims are invalid."""


class GoogleVerificationUnavailableError(Exception):
    """Raised when Google's public signing keys cannot be retrieved."""


@dataclass(frozen=True, slots=True)
class VerifiedGoogleIdentity:
    subject: str
    email: str
    normalized_email: str


def _required_claims(claims: dict[str, Any], client_id: str) -> VerifiedGoogleIdentity:
    subject = claims.get("sub")
    email_claim = claims.get("email")
    expiration = claims.get("exp")

    valid_expiration = (
        isinstance(expiration, (int, float))
        and not isinstance(expiration, bool)
        and expiration > time()
    )
    if (
        claims.get("aud") != client_id
        or claims.get("iss") not in _GOOGLE_ISSUERS
        or not valid_expiration
        or claims.get("email_verified") is not True
        or not isinstance(subject, str)
        or not subject
        or len(subject) > 255
        or not isinstance(email_claim, str)
    ):
        raise InvalidGoogleTokenError

    try:
        email = validate_and_normalize_email(email_claim)
    except InvalidEmailError as error:
        raise InvalidGoogleTokenError from error

    return VerifiedGoogleIdentity(
        subject=subject,
        email=email.address,
        normalized_email=email.normalized,
    )


def verify_google_id_token(raw_token: str, client_id: str) -> VerifiedGoogleIdentity:
    """Validate a Google ID token and extract only trusted identity claims."""
    try:
        claims = google_token_verifier(raw_token, Request(), client_id)
    except TransportError as error:
        raise GoogleVerificationUnavailableError from error
    except ValueError as error:
        raise InvalidGoogleTokenError from error

    return _required_claims(claims, client_id)


__all__ = [
    "GoogleVerificationUnavailableError",
    "InvalidGoogleTokenError",
    "VerifiedGoogleIdentity",
    "verify_google_id_token",
]
