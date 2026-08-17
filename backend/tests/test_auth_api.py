from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import time

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select

from app import main
from app.auth import router as auth_router
from app.auth.google import (
    GoogleVerificationUnavailableError,
    InvalidGoogleTokenError,
    VerifiedGoogleIdentity,
)
from app.auth.tokens import generate_token, hash_token
from app.models import AuthenticationIdentity, User, UserSession

BACKEND_ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.integration
FRONTEND_ORIGIN = "http://localhost:5173"


@pytest.fixture
def auth_client(
    empty_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", empty_database_url)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")

    with TestClient(main.app) as client:
        yield client


def csrf_headers(client: TestClient) -> dict[str, str]:
    csrf_token = client.cookies.get("mfp_csrf")
    assert csrf_token is not None
    return {"Origin": FRONTEND_ORIGIN, "X-CSRF-Token": csrf_token}


def ensure_csrf_cookie(client: TestClient) -> None:
    if client.cookies.get("mfp_csrf") is None:
        response = client.get("/auth/csrf")
        assert response.status_code == 204


def register(client: TestClient, email: str = "person@example.com") -> Response:
    ensure_csrf_cookie(client)
    return client.post(
        "/auth/register",
        json={"email": email, "password": "correct horse battery staple"},
        headers=csrf_headers(client),
    )


def test_registration_creates_account_and_opaque_cookie_session(auth_client: TestClient) -> None:
    response = register(auth_client, "Person@EXAMPLE.com")

    assert response.status_code == 201
    assert response.json()["email"] == "person@example.com"
    assert "password" not in response.json()

    session_token = auth_client.cookies.get("mfp_session")
    assert session_token is not None
    assert auth_client.cookies.get("mfp_csrf") is not None
    cookie_headers = response.headers.get_list("set-cookie")
    session_cookie_header = next(
        header for header in cookie_headers if header.startswith("mfp_session=")
    )
    assert "HttpOnly" in session_cookie_header
    assert "SameSite=lax" in session_cookie_header
    assert "Path=/" in session_cookie_header
    assert "Domain=" not in session_cookie_header
    assert "Secure" not in session_cookie_header
    csrf_cookie_header = next(header for header in cookie_headers if header.startswith("mfp_csrf="))
    assert "HttpOnly" not in csrf_cookie_header
    assert "SameSite=lax" in csrf_cookie_header

    me_response = auth_client.get("/auth/me")
    assert me_response.status_code == 200
    assert me_response.json() == response.json()

    factory = main.app.state.database_session_factory
    with factory() as database_session:
        stored_session = database_session.scalar(select(UserSession))
        assert stored_session is not None
        assert len(stored_session.token_hash) == 32
        assert stored_session.token_hash != session_token.encode("ascii")


def test_duplicate_registration_returns_provider_neutral_conflict(
    auth_client: TestClient,
) -> None:
    assert register(auth_client).status_code == 201

    response = register(auth_client, "PERSON@example.com")

    assert response.status_code == 409
    assert response.json() == {"detail": "Unable to create an account with those credentials."}


def test_login_uses_generic_error_for_unknown_email_and_wrong_password(
    auth_client: TestClient,
) -> None:
    assert register(auth_client).status_code == 201
    expected_error = {"detail": "Invalid email or password."}

    unknown_response = auth_client.post(
        "/auth/login",
        json={"email": "unknown@example.com", "password": "an incorrect password"},
        headers=csrf_headers(auth_client),
    )
    wrong_password_response = auth_client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "an incorrect password"},
        headers=csrf_headers(auth_client),
    )

    assert unknown_response.status_code == 401
    assert wrong_password_response.status_code == 401
    assert unknown_response.json() == expected_error
    assert wrong_password_response.json() == expected_error


def test_logout_revokes_session_and_clears_cookies(auth_client: TestClient) -> None:
    assert register(auth_client).status_code == 201

    logout_response = auth_client.post("/auth/logout", headers=csrf_headers(auth_client))

    assert logout_response.status_code == 204
    assert logout_response.content == b""
    assert auth_client.cookies.get("mfp_session") is None
    assert auth_client.cookies.get("mfp_csrf") is None
    assert auth_client.get("/auth/me").status_code == 401


def test_successful_login_issues_fresh_session(auth_client: TestClient) -> None:
    assert register(auth_client).status_code == 201
    original_token = auth_client.cookies.get("mfp_session")
    assert auth_client.post("/auth/logout", headers=csrf_headers(auth_client)).status_code == 204
    ensure_csrf_cookie(auth_client)

    response = auth_client.post(
        "/auth/login",
        json={
            "email": "PERSON@example.com",
            "password": "correct horse battery staple",
        },
        headers=csrf_headers(auth_client),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "person@example.com"
    assert auth_client.cookies.get("mfp_session") not in (None, original_token)
    assert auth_client.get("/auth/me").status_code == 200


def test_registration_rejects_invalid_email_and_short_password(auth_client: TestClient) -> None:
    ensure_csrf_cookie(auth_client)
    invalid_email_response = auth_client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "long enough password"},
        headers=csrf_headers(auth_client),
    )
    short_password_response = auth_client.post(
        "/auth/register",
        json={"email": "person@example.com", "password": "short"},
        headers=csrf_headers(auth_client),
    )

    assert invalid_email_response.status_code == 422
    assert invalid_email_response.json() == {"detail": "Enter a valid email address."}
    assert short_password_response.status_code == 422
    assert short_password_response.json() == {
        "detail": "Password must contain at least 8 characters."
    }


def test_authentication_mutations_require_matching_csrf_and_local_origin(
    auth_client: TestClient,
) -> None:
    ensure_csrf_cookie(auth_client)
    payload = {"email": "person@example.com", "password": "correct horse battery staple"}

    missing_header = auth_client.post(
        "/auth/register",
        json=payload,
        headers={"Origin": FRONTEND_ORIGIN},
    )
    wrong_origin = auth_client.post(
        "/auth/register",
        json=payload,
        headers={"Origin": "https://attacker.example", "X-CSRF-Token": "x" * 43},
    )
    mismatched_token = auth_client.post(
        "/auth/register",
        json=payload,
        headers={"Origin": FRONTEND_ORIGIN, "X-CSRF-Token": "x" * 43},
    )

    assert missing_header.status_code == 403
    assert wrong_origin.status_code == 403
    assert mismatched_token.status_code == 403
    assert register(auth_client).status_code == 201


def test_logout_requires_session_bound_csrf_token(auth_client: TestClient) -> None:
    assert register(auth_client).status_code == 201

    response = auth_client.post(
        "/auth/logout",
        headers={"Origin": FRONTEND_ORIGIN, "X-CSRF-Token": "x" * 43},
    )

    assert response.status_code == 403
    assert auth_client.get("/auth/me").status_code == 200


def test_protected_endpoint_rejects_missing_and_malformed_sessions(
    auth_client: TestClient,
) -> None:
    assert auth_client.get("/protected").status_code == 401
    auth_client.cookies.set("mfp_session", "not-a-valid-token")

    response = auth_client.get("/protected")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_protected_endpoint_rejects_unknown_well_formed_session(
    auth_client: TestClient,
) -> None:
    auth_client.cookies.set("mfp_session", generate_token())

    response = auth_client.get("/protected")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_protected_endpoint_accepts_active_session(auth_client: TestClient) -> None:
    registration = register(auth_client)

    response = auth_client.get("/protected")

    assert response.status_code == 200
    assert response.json() == {
        "message": "You are authenticated.",
        "user_id": registration.json()["id"],
    }


def test_expired_session_is_rejected(auth_client: TestClient) -> None:
    assert register(auth_client).status_code == 201
    session_token = auth_client.cookies.get("mfp_session")
    assert session_token is not None

    factory = main.app.state.database_session_factory
    with factory.begin() as database_session:
        stored_session = database_session.scalar(
            select(UserSession).where(UserSession.token_hash == hash_token(session_token))
        )
        assert stored_session is not None
        stored_session.expires_at = stored_session.created_at + timedelta(microseconds=1)

    assert auth_client.get("/protected").status_code == 401


def test_revoked_session_is_rejected(auth_client: TestClient) -> None:
    assert register(auth_client).status_code == 201
    session_token = auth_client.cookies.get("mfp_session")
    assert session_token is not None

    factory = main.app.state.database_session_factory
    with factory.begin() as database_session:
        stored_session = database_session.scalar(
            select(UserSession).where(UserSession.token_hash == hash_token(session_token))
        )
        assert stored_session is not None
        stored_session.revoked_at = datetime.now(UTC)

    assert auth_client.get("/protected").status_code == 401


def test_cors_allows_only_documented_local_origin(auth_client: TestClient) -> None:
    allowed = auth_client.options(
        "/auth/register",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token",
        },
    )
    denied = auth_client.options(
        "/auth/register",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_api_responses_are_not_cacheable(auth_client: TestClient) -> None:
    assert auth_client.get("/auth/me").headers["cache-control"] == "no-store"
    assert auth_client.get("/health").headers["cache-control"] == "no-store"


def google_sign_in(client: TestClient, token: str = "signed-google-token") -> Response:
    ensure_csrf_cookie(client)
    return client.post(
        "/auth/google",
        json={"id_token": token},
        headers=csrf_headers(client),
    )


def test_google_sign_in_creates_identity_and_application_session(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: VerifiedGoogleIdentity(
            subject="google-subject-123",
            email="person@example.com",
            normalized_email="person@example.com",
            issued_at=time(),
        ),
    )

    response = google_sign_in(auth_client)

    assert response.status_code == 200
    assert response.json()["email"] == "person@example.com"
    assert auth_client.cookies.get("mfp_session") is not None
    assert auth_client.get("/auth/me").json() == response.json()

    factory = main.app.state.database_session_factory
    with factory() as database_session:
        identity = database_session.scalar(select(AuthenticationIdentity))
        assert identity is not None
        assert identity.provider == "google"
        assert identity.provider_subject == "google-subject-123"
        assert identity.email_verified is True
        assert identity.password_hash is None


def test_returning_google_subject_reuses_user_and_issues_fresh_session(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: VerifiedGoogleIdentity(
            subject="google-subject-123",
            email="person@example.com",
            normalized_email="person@example.com",
            issued_at=time(),
        ),
    )
    first_response = google_sign_in(auth_client)
    first_session_token = auth_client.cookies.get("mfp_session")
    assert first_response.status_code == 200
    assert auth_client.post("/auth/logout", headers=csrf_headers(auth_client)).status_code == 204

    second_response = google_sign_in(auth_client, "new-signed-google-token")

    assert second_response.status_code == 200
    assert second_response.json()["id"] == first_response.json()["id"]
    assert auth_client.cookies.get("mfp_session") not in (None, first_session_token)

    factory = main.app.state.database_session_factory
    with factory() as database_session:
        assert len(database_session.scalars(select(User)).all()) == 1
        assert len(database_session.scalars(select(AuthenticationIdentity)).all()) == 1


def test_google_email_collision_does_not_link_password_account(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert register(auth_client).status_code == 201
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: VerifiedGoogleIdentity(
            subject="new-google-subject",
            email="person@example.com",
            normalized_email="person@example.com",
            issued_at=time(),
        ),
    )

    response = google_sign_in(auth_client)

    assert response.status_code == 409
    assert response.json() == {"detail": "Unable to sign in with Google."}
    factory = main.app.state.database_session_factory
    with factory() as database_session:
        identities = database_session.scalars(select(AuthenticationIdentity)).all()
        assert len(identities) == 1
        assert identities[0].provider == "password"


def test_google_sign_in_returns_generic_error_for_invalid_token(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject(*_arguments: object) -> None:
        raise InvalidGoogleTokenError

    monkeypatch.setattr(auth_router, "verify_google_id_token", reject)

    response = google_sign_in(auth_client, "invalid-google-token")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unable to authenticate with Google."}


def test_google_sign_in_requires_csrf_before_token_verification(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verify_called = False

    def verify(*_arguments: object) -> None:
        nonlocal verify_called
        verify_called = True

    monkeypatch.setattr(auth_router, "verify_google_id_token", verify)

    response = auth_client.post(
        "/auth/google",
        json={"id_token": "signed-google-token"},
        headers={"Origin": FRONTEND_ORIGIN},
    )

    assert response.status_code == 403
    assert verify_called is False


def test_password_registration_cannot_claim_existing_google_email(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: VerifiedGoogleIdentity(
            subject="google-subject-123",
            email="person@example.com",
            normalized_email="person@example.com",
            issued_at=time(),
        ),
    )
    assert google_sign_in(auth_client).status_code == 200

    response = register(auth_client, "PERSON@example.com")

    assert response.status_code == 409
    assert response.json() == {"detail": "Unable to create an account with those credentials."}
    factory = main.app.state.database_session_factory
    with factory() as database_session:
        identities = database_session.scalars(select(AuthenticationIdentity)).all()
        assert len(identities) == 1
        assert identities[0].provider == "google"


def test_google_verification_outage_returns_temporary_unavailability(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_arguments: object) -> None:
        raise GoogleVerificationUnavailableError

    monkeypatch.setattr(auth_router, "verify_google_id_token", fail)

    response = google_sign_in(auth_client)

    assert response.status_code == 503
    assert response.json() == {"detail": "Google Sign-In is temporarily unavailable."}


def test_google_sign_in_reports_missing_local_configuration(
    auth_client: TestClient,
) -> None:
    main.app.state.settings.google_client_id = None

    response = google_sign_in(auth_client)

    assert response.status_code == 503
    assert response.json() == {"detail": "Google Sign-In is not configured."}
