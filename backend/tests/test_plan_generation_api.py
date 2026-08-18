from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import main
from app.models import Plan
from app.plan_generation import workflow
from app.plan_generation.errors import PlanGenerationError, PlanGenerationFailureCode
from app.plan_generation.schemas import ClaudePlanRequest, GeneratedPlan
from app.profile.schemas import ProfileInput

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ORIGIN = "http://localhost:5173"
pytestmark = pytest.mark.integration


@pytest.fixture
def generation_client(
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


def valid_generated_plan() -> GeneratedPlan:
    exercise = {
        "name": "Bodyweight squat",
        "prescription": "3 sets of 8-10",
    }
    session = {
        "day_label": "Day 1",
        "focus": "Full body",
        "duration_minutes": 45,
        "exercises": [exercise, {**exercise, "name": "Dumbbell row"}],
    }
    return GeneratedPlan.model_validate(
        {
            "schema_version": 2,
            "title": "Three-day general fitness plan",
            "overview": "A balanced routine using the available equipment.",
            "workout_plan": {
                "sessions": [
                    session,
                    {**session, "day_label": "Day 2"},
                    {**session, "day_label": "Day 3"},
                ],
                "progression_guidance": "Add repetitions gradually.",
                "recovery_guidance": "Leave non-training days between sessions.",
            },
            "nutrition_plan": {
                "meal_ideas": [
                    {"meal_name": "Breakfast", "foods": ["Oats", "Fruit"]},
                    {"meal_name": "Lunch", "foods": ["Beans", "Rice"]},
                    {"meal_name": "Dinner", "foods": ["Lentils", "Vegetables"]},
                ],
                "daily_guidance": "Choose portions that match appetite.",
                "hydration_guidance": "Drink water regularly and respond to thirst.",
            },
        }
    )


def save_profile(client: TestClient, profile: dict[str, object] | None = None) -> None:
    response = client.put(
        "/profile",
        json=profile or valid_profile(),
        headers=csrf_headers(client),
    )
    assert response.status_code == 200


def test_generation_requires_authentication_and_csrf(generation_client: TestClient) -> None:
    assert generation_client.post("/plans/generate").status_code == 401
    register(generation_client)
    save_profile(generation_client)

    response = generation_client.post("/plans/generate")

    assert response.status_code == 403


def test_generation_uses_authenticated_profile_and_calculations(
    generation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register(generation_client)
    save_profile(generation_client)
    captured_request: ClaudePlanRequest | None = None

    def generate(request: ClaudePlanRequest, _settings: object) -> GeneratedPlan:
        nonlocal captured_request
        captured_request = request
        return valid_generated_plan()

    monkeypatch.setattr(workflow, "generate_structured_plan", generate)

    response = generation_client.post("/plans/generate", headers=csrf_headers(generation_client))

    assert response.status_code == 201
    response_body = response.json()
    generated_plan = valid_generated_plan().model_dump(mode="json")
    for field_name, value in generated_plan.items():
        assert response_body[field_name] == value
    assert response_body["status"] == "inactive"
    assert response_body["archived_at"] is None
    assert response_body["profile_snapshot"]["profile"] == valid_profile()
    assert response_body["profile_snapshot"]["calculated_values"] == {
        "calculation_version": 1,
        "sessions_per_week": 3,
        "minutes_per_session": 45,
        "weekly_available_minutes": 135,
        "non_training_days_per_week": 4,
    }
    assert captured_request is not None
    assert captured_request.profile_data == ProfileInput.model_validate(valid_profile())
    assert captured_request.calculated_values.weekly_available_minutes == 135
    assert captured_request.calculated_values.non_training_days_per_week == 4
    factory = main.app.state.database_session_factory
    with factory() as database_session:
        stored_plans = database_session.scalars(select(Plan)).all()
        assert len(stored_plans) == 1
        assert stored_plans[0].overview == generated_plan["overview"]
        assert stored_plans[0].profile_snapshot == response_body["profile_snapshot"]


def test_missing_profile_is_explicit_and_cannot_select_another_users_profile(
    generation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register(generation_client, "first@example.com")
    save_profile(generation_client)
    assert (
        generation_client.post("/auth/logout", headers=csrf_headers(generation_client)).status_code
        == 204
    )
    register(generation_client, "second@example.com")
    called = False

    def should_not_generate(_request: ClaudePlanRequest, _settings: object) -> GeneratedPlan:
        nonlocal called
        called = True
        return valid_generated_plan()

    monkeypatch.setattr(workflow, "generate_structured_plan", should_not_generate)

    response = generation_client.post("/plans/generate", headers=csrf_headers(generation_client))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "missing_profile"
    assert called is False


def test_unsafe_profile_is_rejected_before_provider_call(
    generation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register(generation_client)
    save_profile(
        generation_client,
        valid_profile(wellness_constraints=["I need rehabilitation after an injury"]),
    )
    called = False

    def should_not_generate(_request: ClaudePlanRequest, _settings: object) -> GeneratedPlan:
        nonlocal called
        called = True
        return valid_generated_plan()

    monkeypatch.setattr(workflow, "generate_structured_plan", should_not_generate)

    response = generation_client.post("/plans/generate", headers=csrf_headers(generation_client))

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "unsafe_profile",
        "message": "The saved profile is outside MyFitnessPlan's general-wellness scope.",
        "issues": ["medical_or_rehabilitation_request"],
    }
    assert called is False


@pytest.mark.parametrize(
    ("failure", "expected_status", "expected_code"),
    [
        (PlanGenerationFailureCode.MISSING_CONFIGURATION, 503, "claude_unavailable"),
        (PlanGenerationFailureCode.TIMEOUT, 503, "provider_unavailable"),
        (PlanGenerationFailureCode.PROVIDER_REJECTION, 502, "provider_failure"),
        (PlanGenerationFailureCode.INVALID_JSON, 502, "invalid_model_output"),
    ],
)
def test_provider_failures_are_mapped_to_explicit_safe_api_errors(
    generation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    failure: PlanGenerationFailureCode,
    expected_status: int,
    expected_code: str,
) -> None:
    register(generation_client)
    save_profile(generation_client)

    def fail(_request: ClaudePlanRequest, _settings: object) -> GeneratedPlan:
        raise PlanGenerationError(failure, "Safe provider failure message.")

    monkeypatch.setattr(workflow, "generate_structured_plan", fail)

    response = generation_client.post("/plans/generate", headers=csrf_headers(generation_client))

    assert response.status_code == expected_status
    assert response.json()["detail"] == {
        "code": expected_code,
        "message": "Safe provider failure message.",
    }


def test_unsafe_generated_content_is_rejected(
    generation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register(generation_client)
    save_profile(generation_client)
    unsafe_plan = valid_generated_plan().model_copy(deep=True)
    unsafe_plan.nutrition_plan.daily_guidance = "Eat exactly 1,200 calories every day."
    monkeypatch.setattr(workflow, "generate_structured_plan", lambda *_args: unsafe_plan)

    response = generation_client.post("/plans/generate", headers=csrf_headers(generation_client))

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "unsafe_model_output"
    assert response.json()["detail"]["issues"] == ["unsupported_nutrition_target"]

    factory = main.app.state.database_session_factory
    with factory() as database_session:
        assert database_session.scalars(select(Plan)).all() == []


def test_plan_history_details_and_profile_snapshot_survive_profile_changes(
    generation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register(generation_client)
    original_profile = valid_profile()
    save_profile(generation_client, original_profile)
    monkeypatch.setattr(workflow, "generate_structured_plan", lambda *_args: valid_generated_plan())

    create_response = generation_client.post(
        "/plans/generate", headers=csrf_headers(generation_client)
    )
    plan_id = create_response.json()["id"]
    save_profile(generation_client, valid_profile(days_per_week=4, session_minutes=30))

    history_response = generation_client.get("/plans")
    detail_response = generation_client.get(f"/plans/{plan_id}")

    assert history_response.status_code == 200
    assert history_response.json() == [
        {
            "id": plan_id,
            "title": valid_generated_plan().title,
            "status": "inactive",
            "created_at": create_response.json()["created_at"],
            "updated_at": create_response.json()["updated_at"],
            "archived_at": None,
        }
    ]
    assert detail_response.status_code == 200
    assert detail_response.json()["profile_snapshot"]["profile"] == original_profile
    assert (
        detail_response.json()["profile_snapshot"]["calculated_values"]["weekly_available_minutes"]
        == 135
    )


def test_selecting_active_plan_and_archiving_preserve_lifecycle_invariants(
    generation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register(generation_client)
    save_profile(generation_client)
    monkeypatch.setattr(workflow, "generate_structured_plan", lambda *_args: valid_generated_plan())
    first_id = generation_client.post(
        "/plans/generate", headers=csrf_headers(generation_client)
    ).json()["id"]
    second_id = generation_client.post(
        "/plans/generate", headers=csrf_headers(generation_client)
    ).json()["id"]

    first_activation = generation_client.post(
        f"/plans/{first_id}/activate", headers=csrf_headers(generation_client)
    )
    second_activation = generation_client.post(
        f"/plans/{second_id}/activate", headers=csrf_headers(generation_client)
    )
    archived = generation_client.post(
        f"/plans/{second_id}/archive", headers=csrf_headers(generation_client)
    )
    reactivation = generation_client.post(
        f"/plans/{second_id}/activate", headers=csrf_headers(generation_client)
    )

    assert first_activation.status_code == 200
    assert first_activation.json()["status"] == "active"
    assert second_activation.status_code == 200
    assert second_activation.json()["status"] == "active"
    assert generation_client.get(f"/plans/{first_id}").json()["status"] == "inactive"
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert archived.json()["archived_at"] is not None
    assert reactivation.status_code == 409
    assert reactivation.json()["detail"]["code"] == "archived_plan"

    factory = main.app.state.database_session_factory
    with factory() as database_session:
        plans = database_session.scalars(select(Plan)).all()
        assert sum(plan.status == "active" for plan in plans) == 0


def test_plan_lifecycle_ownership_is_derived_from_session(
    generation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register(generation_client, "first@example.com")
    save_profile(generation_client)
    monkeypatch.setattr(workflow, "generate_structured_plan", lambda *_args: valid_generated_plan())
    plan_id = generation_client.post(
        "/plans/generate", headers=csrf_headers(generation_client)
    ).json()["id"]
    assert (
        generation_client.post("/auth/logout", headers=csrf_headers(generation_client)).status_code
        == 204
    )
    register(generation_client, "second@example.com")

    assert generation_client.get("/plans").json() == []
    assert generation_client.get(f"/plans/{plan_id}").status_code == 404
    assert (
        generation_client.post(
            f"/plans/{plan_id}/activate", headers=csrf_headers(generation_client)
        ).status_code
        == 404
    )
    assert (
        generation_client.post(
            f"/plans/{plan_id}/archive", headers=csrf_headers(generation_client)
        ).status_code
        == 404
    )


def test_plan_lifecycle_mutations_require_session_bound_csrf(
    generation_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register(generation_client)
    save_profile(generation_client)
    monkeypatch.setattr(workflow, "generate_structured_plan", lambda *_args: valid_generated_plan())
    plan_id = generation_client.post(
        "/plans/generate", headers=csrf_headers(generation_client)
    ).json()["id"]

    assert generation_client.post(f"/plans/{plan_id}/activate").status_code == 403
    assert generation_client.post(f"/plans/{plan_id}/archive").status_code == 403
    assert generation_client.get(f"/plans/{plan_id}").json()["status"] == "inactive"
