from dataclasses import dataclass

from email_validator import EmailNotValidError, validate_email
from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError
from pwdlib.hashers.argon2 import Argon2Hasher

MINIMUM_PASSWORD_LENGTH = 8
MAXIMUM_PASSWORD_LENGTH = 128

# This explicit Argon2id configuration meets OWASP's baseline while remaining practical locally.
_PASSWORD_HASH = PasswordHash(
    (
        Argon2Hasher(
            memory_cost=19_456,
            time_cost=2,
            parallelism=1,
        ),
    )
)

# This is not a credential. It gives an unknown account the same expensive verification path.
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=19456,t=2,p=1$"
    "qJ/Ps/Y6bHs299glpllc5g$"
    "aH2srBqeT4UJNBnnqY0LmLl+CJi+UHYaCmwX5qxodkg"
)
_DUMMY_PASSWORD = "dummy-password-used-only-for-timing"


class InvalidEmailError(ValueError):
    """Raised when an email address cannot be safely used as an identity."""


class InvalidPasswordError(ValueError):
    """Raised when a new password does not meet the application policy."""


@dataclass(frozen=True, slots=True)
class ValidatedEmail:
    """A validated address plus its case-insensitive database lookup key."""

    address: str
    normalized: str


@dataclass(frozen=True, slots=True)
class PasswordVerification:
    """A verification result and an optional upgraded password hash."""

    valid: bool
    updated_hash: str | None = None


def validate_and_normalize_email(value: str) -> ValidatedEmail:
    """Validate an email and produce the canonical case-insensitive lookup value."""
    try:
        result = validate_email(
            value.strip(),
            check_deliverability=False,
            allow_smtputf8=False,
        )
    except EmailNotValidError as error:
        raise InvalidEmailError("Enter a valid email address.") from error

    address = result.normalized
    return ValidatedEmail(address=address, normalized=address.lower())


def validate_new_password(password: str) -> None:
    """Enforce length without trimming or restricting character classes."""
    if len(password) < MINIMUM_PASSWORD_LENGTH:
        raise InvalidPasswordError(
            f"Password must contain at least {MINIMUM_PASSWORD_LENGTH} characters."
        )
    if len(password) > MAXIMUM_PASSWORD_LENGTH:
        raise InvalidPasswordError(
            f"Password must contain at most {MAXIMUM_PASSWORD_LENGTH} characters."
        )


def hash_password(password: str) -> str:
    """Validate and hash a new password with Argon2id and a unique salt."""
    validate_new_password(password)
    return _PASSWORD_HASH.hash(password)


def verify_password(password: str, stored_hash: str | None) -> PasswordVerification:
    """Verify a password while preserving costly work for unknown accounts."""
    if len(password) > MAXIMUM_PASSWORD_LENGTH:
        _PASSWORD_HASH.verify(_DUMMY_PASSWORD, _DUMMY_PASSWORD_HASH)
        return PasswordVerification(valid=False)

    password_hash = stored_hash or _DUMMY_PASSWORD_HASH

    try:
        valid, updated_hash = _PASSWORD_HASH.verify_and_update(password, password_hash)
    except PwdlibError:
        _PASSWORD_HASH.verify(password, _DUMMY_PASSWORD_HASH)
        return PasswordVerification(valid=False)

    if stored_hash is None:
        return PasswordVerification(valid=False)
    return PasswordVerification(valid=valid, updated_hash=updated_hash if valid else None)
