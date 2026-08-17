from time import time
from typing import Any

import pytest
from google.auth.exceptions import TransportError

from app.auth import google
from app.auth.google import (
    GoogleVerificationUnavailableError,
    InvalidGoogleTokenError,
    verify_google_id_token,
)


def valid_claims() -> dict[str, Any]:
    return {
        "aud": "test-client-id",
        "iss": "https://accounts.google.com",
        "exp": time() + 300,
        "iat": time(),
        "sub": "google-subject-123",
        "email": "Person@Example.com",
        "email_verified": True,
    }


def test_google_library_verification_uses_expected_audience_and_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_verify(raw_token: str, request: object, audience: str) -> dict[str, Any]:
        captured.update(token=raw_token, request=request, audience=audience)
        return valid_claims()

    monkeypatch.setattr(google, "google_token_verifier", fake_verify)

    identity = verify_google_id_token("signed-google-token", "test-client-id")

    assert captured["token"] == "signed-google-token"
    assert captured["audience"] == "test-client-id"
    assert identity.subject == "google-subject-123"
    assert identity.email == "Person@example.com"
    assert identity.normalized_email == "person@example.com"
    assert identity.issued_at <= time()


@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("aud", "wrong-client"),
        ("iss", "https://issuer.example"),
        ("exp", 0),
        ("iat", True),
        ("sub", ""),
        ("email", "not-an-email"),
        ("email_verified", False),
        ("email_verified", "true"),
    ],
)
def test_google_verification_rejects_invalid_required_claims(
    monkeypatch: pytest.MonkeyPatch,
    claim: str,
    value: object,
) -> None:
    claims = valid_claims()
    claims[claim] = value
    monkeypatch.setattr(
        google,
        "google_token_verifier",
        lambda *_arguments: claims,
    )

    with pytest.raises(InvalidGoogleTokenError):
        verify_google_id_token("signed-google-token", "test-client-id")


def test_google_library_rejection_is_an_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*_arguments: object) -> None:
        raise ValueError("invalid signature")

    monkeypatch.setattr(google, "google_token_verifier", reject)

    with pytest.raises(InvalidGoogleTokenError):
        verify_google_id_token("invalid-google-token", "test-client-id")


def test_google_key_retrieval_failure_is_temporarily_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_arguments: object) -> None:
        raise TransportError("network unavailable")  # type: ignore[no-untyped-call]

    monkeypatch.setattr(google, "google_token_verifier", fail)

    with pytest.raises(GoogleVerificationUnavailableError):
        verify_google_id_token("signed-google-token", "test-client-id")
