from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import main
from app.models import Profile

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ORIGIN = "http://localhost:5173"
pytestmark = pytest.mark.integration


@pytest.fixture
def profile_client(
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


def valid_profile(**overrides: object) -> dict[str, object]:
    profile: dict[str, object] = {
        "display_name": "Jordan",
        "fitness_goal": "general_fitness",
        "experience_level": "beginner",
        "days_per_week": 3,
        "session_minutes": 45,
        "equipment": ["Dumbbells", "Yoga mat"],
        "dietary_preferences": ["Vegetarian"],
        "wellness_constraints": ["Prefer low-impact movements"],
    }
    profile.update(overrides)
    return profile


def test_profile_endpoints_require_authentication(profile_client: TestClient) -> None:
    assert profile_client.get("/profile").status_code == 401
    assert profile_client.get("/auth/csrf").status_code == 204

    response = profile_client.put(
        "/profile",
        json=valid_profile(),
        headers=csrf_headers(profile_client),
    )

    assert response.status_code == 401


def test_missing_profile_returns_not_found(profile_client: TestClient) -> None:
    register(profile_client)

    response = profile_client.get("/profile")

    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found."}


def test_create_read_and_replace_profile(profile_client: TestClient) -> None:
    register(profile_client)
    original = valid_profile()

    create_response = profile_client.put(
        "/profile",
        json=original,
        headers=csrf_headers(profile_client),
    )
    read_response = profile_client.get("/profile")
    updated = valid_profile(
        display_name="Jordan Lee",
        fitness_goal="strength",
        days_per_week=4,
        equipment=["Barbell"],
    )
    update_response = profile_client.put(
        "/profile",
        json=updated,
        headers=csrf_headers(profile_client),
    )

    assert create_response.status_code == 200
    assert create_response.json() == original
    assert read_response.json() == original
    assert update_response.status_code == 200
    assert update_response.json() == updated

    factory = main.app.state.database_session_factory
    with factory() as database_session:
        assert len(database_session.scalars(select(Profile)).all()) == 1


def test_profile_ownership_comes_from_authenticated_session(profile_client: TestClient) -> None:
    register(profile_client, "first@example.com")
    assert (
        profile_client.put(
            "/profile",
            json=valid_profile(display_name="First user"),
            headers=csrf_headers(profile_client),
        ).status_code
        == 200
    )
    assert (
        profile_client.post(
            "/auth/logout",
            headers=csrf_headers(profile_client),
        ).status_code
        == 204
    )

    register(profile_client, "second@example.com")

    assert profile_client.get("/profile").status_code == 404
    assert (
        profile_client.put(
            "/profile",
            json=valid_profile(display_name="Second user"),
            headers=csrf_headers(profile_client),
        ).status_code
        == 200
    )

    factory = main.app.state.database_session_factory
    with factory() as database_session:
        profiles = database_session.scalars(select(Profile)).all()
        assert {profile.display_name for profile in profiles} == {"First user", "Second user"}


def test_profile_update_requires_session_bound_csrf(profile_client: TestClient) -> None:
    register(profile_client)

    response = profile_client.put(
        "/profile",
        json=valid_profile(),
        headers={"Origin": FRONTEND_ORIGIN, "X-CSRF-Token": "x" * 43},
    )

    assert response.status_code == 403
    assert profile_client.get("/profile").status_code == 404


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fitness_goal", "medical_rehabilitation"),
        ("experience_level", "expert"),
        ("days_per_week", 0),
        ("days_per_week", 8),
        ("session_minutes", 9),
        ("session_minutes", 181),
        ("equipment", ["Dumbbells", "dumbbells"]),
        ("wellness_constraints", ["x" * 101]),
    ],
)
def test_profile_rejects_invalid_or_unbounded_input(
    profile_client: TestClient,
    field: str,
    value: object,
) -> None:
    register(profile_client)

    response = profile_client.put(
        "/profile",
        json=valid_profile(**{field: value}),
        headers=csrf_headers(profile_client),
    )

    assert response.status_code == 422
    assert profile_client.get("/profile").status_code == 404
