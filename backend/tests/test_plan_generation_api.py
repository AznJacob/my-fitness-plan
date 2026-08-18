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
        "sets": 3,
        "repetitions": "8-10",
        "duration_seconds": None,
        "rest_seconds": 60,
        "instructions": "Use a comfortable range of motion.",
    }
    session = {
        "day_label": "Day 1",
        "focus": "Full body",
        "duration_minutes": 45,
        "warm_up": [exercise],
        "main_workout": [exercise],
        "cool_down": [exercise],
    }
    return GeneratedPlan.model_validate(
        {
            "schema_version": 1,
            "title": "Three-day general fitness plan",
            "overview": "A balanced routine using the available equipment.",
            "workout_plan": {
                "summary": "Three full-body sessions.",
                "sessions": [
                    session,
                    {**session, "day_label": "Day 2"},
                    {**session, "day_label": "Day 3"},
                ],
                "progression_guidance": "Add repetitions gradually.",
                "recovery_guidance": "Leave non-training days between sessions.",
            },
            "nutrition_plan": {
                "summary": "Flexible vegetarian meals using varied whole foods.",
                "daily_templates": [
                    {
                        "day_label": "Every day",
                        "meals": [
                            {
                                "meal_name": "Breakfast",
                                "foods": ["Oats", "Fruit"],
                                "guidance": "Choose portions that match appetite.",
                            },
                            {
                                "meal_name": "Dinner",
                                "foods": ["Beans", "Rice", "Vegetables"],
                                "guidance": "Include a variety of colors.",
                            },
                        ],
                    }
                ],
                "hydration_guidance": "Drink water regularly and respond to thirst.",
                "meal_timing_guidance": "Choose a comfortable, sustainable schedule.",
                "dietary_preference_notes": "All suggestions are vegetarian.",
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

    assert response.status_code == 200
    assert response.json() == valid_generated_plan().model_dump(mode="json")
    assert captured_request is not None
    assert captured_request.profile_data == ProfileInput.model_validate(valid_profile())
    assert captured_request.calculated_values.weekly_available_minutes == 135
    assert captured_request.calculated_values.non_training_days_per_week == 4
    factory = main.app.state.database_session_factory
    with factory() as database_session:
        assert database_session.scalars(select(Plan)).all() == []


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
    unsafe_plan.nutrition_plan.summary = "Eat exactly 1,200 calories every day."
    monkeypatch.setattr(workflow, "generate_structured_plan", lambda *_args: unsafe_plan)

    response = generation_client.post("/plans/generate", headers=csrf_headers(generation_client))

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "unsafe_model_output"
    assert response.json()["detail"]["issues"] == ["unsupported_nutrition_target"]
