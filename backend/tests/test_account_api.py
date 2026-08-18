from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import main
from app.models import AccountDetails

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ORIGIN = "http://localhost:5173"
pytestmark = pytest.mark.integration


@pytest.fixture
def account_client(
    empty_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", empty_database_url)
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    with TestClient(main.app) as client:
        yield client


def csrf_headers(client: TestClient) -> dict[str, str]:
    csrf_token = client.cookies.get("mfp_csrf")
    assert csrf_token is not None
    return {"Origin": FRONTEND_ORIGIN, "X-CSRF-Token": csrf_token}


def register(client: TestClient, email: str = "person@example.com") -> None:
    assert client.get("/auth/csrf").status_code == 204
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "correct horse battery staple"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 201


def valid_details(**overrides: object) -> dict[str, object]:
    details: dict[str, object] = {
        "username": "Jordan",
        "height_cm": "180.5",
        "weight_kg": "82.4",
    }
    details.update(overrides)
    return details


def test_account_details_require_authentication(account_client: TestClient) -> None:
    assert account_client.get("/account/details").status_code == 401
    assert account_client.get("/auth/csrf").status_code == 204
    response = account_client.put(
        "/account/details",
        json=valid_details(),
        headers=csrf_headers(account_client),
    )
    assert response.status_code == 401


def test_missing_account_details_return_not_found(account_client: TestClient) -> None:
    register(account_client)
    response = account_client.get("/account/details")
    assert response.status_code == 404
    assert response.json() == {"detail": "Account details not found."}


def test_create_read_and_replace_account_details(account_client: TestClient) -> None:
    register(account_client)
    original = valid_details()
    create_response = account_client.put(
        "/account/details", json=original, headers=csrf_headers(account_client)
    )
    read_response = account_client.get("/account/details")
    updated = valid_details(username="Jordan Lee", weight_kg="80.0")
    update_response = account_client.put(
        "/account/details", json=updated, headers=csrf_headers(account_client)
    )

    assert create_response.status_code == 200
    assert create_response.json() == original
    assert read_response.json() == original
    assert update_response.json() == updated
    factory = main.app.state.database_session_factory
    with factory() as database_session:
        assert len(database_session.scalars(select(AccountDetails)).all()) == 1


def test_account_details_ownership_comes_from_session(account_client: TestClient) -> None:
    register(account_client, "first@example.com")
    assert (
        account_client.put(
            "/account/details",
            json=valid_details(username="First user"),
            headers=csrf_headers(account_client),
        ).status_code
        == 200
    )
    logout_response = account_client.post("/auth/logout", headers=csrf_headers(account_client))
    assert logout_response.status_code == 204
    register(account_client, "second@example.com")
    assert account_client.get("/account/details").status_code == 404


def test_account_details_update_requires_session_bound_csrf(account_client: TestClient) -> None:
    register(account_client)
    response = account_client.put(
        "/account/details",
        json=valid_details(),
        headers={"Origin": FRONTEND_ORIGIN, "X-CSRF-Token": "x" * 43},
    )
    assert response.status_code == 403
    assert account_client.get("/account/details").status_code == 404


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("username", "x" * 101),
        ("height_cm", 49.9),
        ("height_cm", 260.1),
        ("weight_kg", 19.9),
        ("weight_kg", 400.1),
    ],
)
def test_account_details_reject_invalid_input(
    account_client: TestClient,
    field: str,
    value: object,
) -> None:
    register(account_client)
    response = account_client.put(
        "/account/details",
        json=valid_details(**{field: value}),
        headers=csrf_headers(account_client),
    )
    assert response.status_code == 422
    assert account_client.get("/account/details").status_code == 404
