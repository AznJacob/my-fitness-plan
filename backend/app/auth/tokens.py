import base64
import binascii
import hashlib
import secrets

TOKEN_BYTES = 32
TOKEN_LENGTH = 43


class InvalidTokenError(ValueError):
    """Raised before a malformed opaque token reaches a database query."""


def generate_token() -> str:
    """Generate a URL-safe token containing 256 bits of randomness."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> bytes:
    """Validate and hash a canonical application token for database lookup."""
    if len(token) != TOKEN_LENGTH:
        raise InvalidTokenError

    try:
        token_bytes = token.encode("ascii")
        decoded = base64.urlsafe_b64decode(token_bytes + b"=")
    except (UnicodeEncodeError, binascii.Error) as error:
        raise InvalidTokenError from error

    if len(decoded) != TOKEN_BYTES or base64.urlsafe_b64encode(decoded).rstrip(b"=") != token_bytes:
        raise InvalidTokenError
    return hashlib.sha256(token_bytes).digest()


__all__ = ["InvalidTokenError", "generate_token", "hash_token"]
