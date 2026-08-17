from collections.abc import Iterator
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
from app.auth.google import VerifiedGoogleIdentity
from app.models import AuthenticationIdentity, User

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ORIGIN = "http://localhost:5173"
PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "a new securely hashed password"
pytestmark = pytest.mark.integration


@pytest.fixture
def linking_client(
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
        assert client.get("/auth/csrf").status_code == 204


def register(client: TestClient, email: str) -> Response:
    ensure_csrf_cookie(client)
    return client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD},
        headers=csrf_headers(client),
    )


def google_sign_in(client: TestClient, token: str = "google-token") -> Response:
    ensure_csrf_cookie(client)
    return client.post(
        "/auth/google",
        json={"id_token": token},
        headers=csrf_headers(client),
    )


def google_identity(
    *,
    subject: str = "google-subject",
    email: str = "person@example.com",
    issued_at: float | None = None,
) -> VerifiedGoogleIdentity:
    return VerifiedGoogleIdentity(
        subject=subject,
        email=email,
        normalized_email=email.lower(),
        issued_at=time() if issued_at is None else issued_at,
    )


def test_password_user_links_google_and_can_sign_in_with_either_method(
    linking_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registration = register(linking_client, "person@example.com")
    assert registration.status_code == 201
    user_id = registration.json()["id"]
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: google_identity(),
    )

    response = linking_client.post(
        "/auth/link/google",
        json={"password": PASSWORD, "id_token": "fresh-google-token"},
        headers=csrf_headers(linking_client),
    )

    assert response.status_code == 200
    assert response.json() == {"password": True, "google": True}
    assert linking_client.get("/auth/methods").json() == response.json()
    assert (
        linking_client.post("/auth/logout", headers=csrf_headers(linking_client)).status_code == 204
    )
    assert google_sign_in(linking_client).json()["id"] == user_id
    assert (
        linking_client.post("/auth/logout", headers=csrf_headers(linking_client)).status_code == 204
    )
    ensure_csrf_cookie(linking_client)
    password_login = linking_client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": PASSWORD},
        headers=csrf_headers(linking_client),
    )
    assert password_login.status_code == 200
    assert password_login.json()["id"] == user_id

    factory = main.app.state.database_session_factory
    with factory() as database_session:
        assert len(database_session.scalars(select(User)).all()) == 1
        identities = database_session.scalars(select(AuthenticationIdentity)).all()
        assert {identity.provider for identity in identities} == {"password", "google"}


def test_google_user_links_password_and_can_sign_in_with_new_password(
    linking_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: google_identity(),
    )
    google_login = google_sign_in(linking_client)
    assert google_login.status_code == 200
    user_id = google_login.json()["id"]

    response = linking_client.post(
        "/auth/link/password",
        json={"new_password": NEW_PASSWORD, "google_id_token": "fresh-google-token"},
        headers=csrf_headers(linking_client),
    )

    assert response.status_code == 200
    assert response.json() == {"password": True, "google": True}
    assert (
        linking_client.post("/auth/logout", headers=csrf_headers(linking_client)).status_code == 204
    )
    ensure_csrf_cookie(linking_client)
    password_login = linking_client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": NEW_PASSWORD},
        headers=csrf_headers(linking_client),
    )
    assert password_login.status_code == 200
    assert password_login.json()["id"] == user_id


def test_link_google_requires_current_password_reauthentication(
    linking_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert register(linking_client, "person@example.com").status_code == 201
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: google_identity(),
    )

    response = linking_client.post(
        "/auth/link/google",
        json={"password": "wrong password", "id_token": "fresh-google-token"},
        headers=csrf_headers(linking_client),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Fresh reauthentication failed."}
    assert linking_client.get("/auth/methods").json() == {"password": True, "google": False}


def test_password_user_cannot_link_google_identity_with_a_different_email(
    linking_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert register(linking_client, "person@example.com").status_code == 201
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: google_identity(email="different@example.com"),
    )

    response = linking_client.post(
        "/auth/link/google",
        json={"password": PASSWORD, "id_token": "fresh-google-token"},
        headers=csrf_headers(linking_client),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Unable to connect that sign-in method."}
    assert linking_client.get("/auth/methods").json() == {"password": True, "google": False}


@pytest.mark.parametrize("endpoint", ["google", "password"])
def test_linking_rejects_stale_google_reauthentication(
    linking_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    stale_identity = google_identity(issued_at=time() - 301)
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: stale_identity,
    )
    if endpoint == "google":
        assert register(linking_client, "person@example.com").status_code == 201
        payload = {"password": PASSWORD, "id_token": "stale-google-token"}
    else:
        fresh_identity = google_identity()
        monkeypatch.setattr(
            auth_router,
            "verify_google_id_token",
            lambda token, *_arguments: fresh_identity if token == "login-token" else stale_identity,
        )
        assert google_sign_in(linking_client, "login-token").status_code == 200
        payload = {"new_password": NEW_PASSWORD, "google_id_token": "stale-google-token"}

    response = linking_client.post(
        f"/auth/link/{endpoint}",
        json=payload,
        headers=csrf_headers(linking_client),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Fresh reauthentication failed."}


def test_matching_google_email_without_owned_subject_cannot_authorize_password_link(
    linking_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_identity = google_identity(subject="owned-subject")
    attacker_identity = google_identity(subject="attacker-subject")
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda token, *_arguments: (
            original_identity if token == "login-token" else attacker_identity
        ),
    )
    assert google_sign_in(linking_client, "login-token").status_code == 200

    response = linking_client.post(
        "/auth/link/password",
        json={"new_password": NEW_PASSWORD, "google_id_token": "attacker-token"},
        headers=csrf_headers(linking_client),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Fresh reauthentication failed."}
    assert linking_client.get("/auth/methods").json() == {"password": False, "google": True}


def test_google_identity_owned_by_another_user_cannot_be_reassigned(
    linking_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_identity = google_identity(subject="claimed-subject", email="owner@example.com")
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: owner_identity,
    )
    owner_login = google_sign_in(linking_client)
    assert owner_login.status_code == 200
    owner_id = owner_login.json()["id"]
    assert (
        linking_client.post("/auth/logout", headers=csrf_headers(linking_client)).status_code == 204
    )
    assert register(linking_client, "attacker@example.com").status_code == 201

    response = linking_client.post(
        "/auth/link/google",
        json={"password": PASSWORD, "id_token": "owner-google-token"},
        headers=csrf_headers(linking_client),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Unable to connect that sign-in method."}
    factory = main.app.state.database_session_factory
    with factory() as database_session:
        identity = database_session.scalar(
            select(AuthenticationIdentity).where(
                AuthenticationIdentity.provider == "google",
                AuthenticationIdentity.provider_subject == "claimed-subject",
            )
        )
        assert identity is not None
        assert str(identity.user_id) == owner_id


def test_linking_requires_session_bound_csrf_before_google_verification(
    linking_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert register(linking_client, "person@example.com").status_code == 201
    verification_called = False

    def verify(*_arguments: object) -> VerifiedGoogleIdentity:
        nonlocal verification_called
        verification_called = True
        return google_identity()

    monkeypatch.setattr(auth_router, "verify_google_id_token", verify)

    response = linking_client.post(
        "/auth/link/google",
        json={"password": PASSWORD, "id_token": "fresh-google-token"},
        headers={"Origin": FRONTEND_ORIGIN},
    )

    assert response.status_code == 403
    assert verification_called is False


def test_linking_an_already_connected_method_is_rejected(
    linking_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert register(linking_client, "person@example.com").status_code == 201
    monkeypatch.setattr(
        auth_router,
        "verify_google_id_token",
        lambda *_arguments: google_identity(),
    )
    first_link = linking_client.post(
        "/auth/link/google",
        json={"password": PASSWORD, "id_token": "fresh-google-token"},
        headers=csrf_headers(linking_client),
    )
    assert first_link.status_code == 200

    response = linking_client.post(
        "/auth/link/google",
        json={"password": PASSWORD, "id_token": "another-fresh-token"},
        headers=csrf_headers(linking_client),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "That sign-in method is already connected."}


def test_connected_methods_requires_authentication(linking_client: TestClient) -> None:
    response = linking_client.get("/auth/methods")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}
