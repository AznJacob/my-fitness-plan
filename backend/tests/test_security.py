import pytest
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.security import (
    MAXIMUM_PASSWORD_LENGTH,
    MINIMUM_PASSWORD_LENGTH,
    InvalidEmailError,
    InvalidPasswordError,
    hash_password,
    validate_and_normalize_email,
    validate_new_password,
    verify_password,
)


def test_email_validation_normalizes_whitespace_case_and_domain() -> None:
    email = validate_and_normalize_email("  Person@EXAMPLE.com  ")

    assert email.address == "Person@example.com"
    assert email.normalized == "person@example.com"


@pytest.mark.parametrize(
    "email",
    [
        "not-an-email",
        "Name <person@example.com>",
        "person@localhost",
        "üser@example.com",
    ],
)
def test_email_validation_rejects_unsafe_identity_addresses(email: str) -> None:
    with pytest.raises(InvalidEmailError, match="Enter a valid email address"):
        validate_and_normalize_email(email)


def test_password_policy_accepts_long_passphrases_and_all_character_classes() -> None:
    validate_new_password("correct horse battery staple")
    validate_new_password("alllowercase-ok")
    validate_new_password("spaces and unicode 🔒 are accepted")


@pytest.mark.parametrize(
    ("password", "expected_message"),
    [
        ("x" * (MINIMUM_PASSWORD_LENGTH - 1), "at least 8"),
        ("x" * (MAXIMUM_PASSWORD_LENGTH + 1), "at most 128"),
    ],
)
def test_password_policy_rejects_out_of_range_lengths(
    password: str,
    expected_message: str,
) -> None:
    with pytest.raises(InvalidPasswordError, match=expected_message):
        validate_new_password(password)


def test_password_hash_uses_argon2id_and_a_unique_salt() -> None:
    password = "a sufficiently long password"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash.startswith("$argon2id$")
    assert second_hash.startswith("$argon2id$")
    assert first_hash != second_hash


def test_password_verification_accepts_match_and_rejects_mismatch() -> None:
    stored_hash = hash_password("a sufficiently long password")

    assert verify_password("a sufficiently long password", stored_hash).valid is True
    assert verify_password("the wrong password", stored_hash).valid is False


def test_password_verification_rejects_missing_or_malformed_hash() -> None:
    password = "a sufficiently long password"

    assert verify_password(password, None).valid is False
    assert verify_password(password, "not-a-password-hash").valid is False


def test_password_verification_returns_an_upgrade_for_weaker_argon2_parameters() -> None:
    weaker_password_hash = PasswordHash(
        (Argon2Hasher(memory_cost=8_192, time_cost=1, parallelism=1),)
    )
    password = "a sufficiently long password"
    stored_hash = weaker_password_hash.hash(password)

    result = verify_password(password, stored_hash)

    assert result.valid is True
    assert result.updated_hash is not None
    assert "m=19456,t=2,p=1" in result.updated_hash


def test_password_verification_rejects_oversized_input() -> None:
    stored_hash = hash_password("a sufficiently long password")

    result = verify_password("x" * (MAXIMUM_PASSWORD_LENGTH + 1), stored_hash)

    assert result.valid is False
