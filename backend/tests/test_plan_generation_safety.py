from copy import deepcopy

from app.plan_generation.safety import (
    GeneratedPlanSafetyIssueCode,
    assess_generated_plan_safety,
)
from app.plan_generation.schemas import GeneratedPlan
from app.wellness.schemas import WellnessCalculationResult


def valid_plan_payload() -> dict[str, object]:
    exercise = {
        "name": "Bodyweight squat",
        "sets": 3,
        "repetitions": "8-10",
        "duration_seconds": None,
        "rest_seconds": 60,
        "instructions": "Use a comfortable range of motion and stop if it causes pain.",
    }
    session = {
        "day_label": "Day 1",
        "focus": "Full body",
        "duration_minutes": 45,
        "warm_up": [exercise],
        "main_workout": [exercise],
        "cool_down": [exercise],
    }
    return {
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
            "progression_guidance": "Add repetitions only when movement remains comfortable.",
            "recovery_guidance": "Leave a non-training day between sessions when practical.",
        },
        "nutrition_plan": {
            "summary": "Flexible vegetarian meals built around varied whole foods.",
            "daily_templates": [
                {
                    "day_label": "Every day",
                    "meals": [
                        {
                            "meal_name": "Breakfast",
                            "foods": ["Oats", "Fruit", "Yogurt"],
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
            "meal_timing_guidance": "Use a meal schedule that is comfortable and sustainable.",
            "dietary_preference_notes": "All suggestions are vegetarian.",
        },
    }


def calculations() -> WellnessCalculationResult:
    return WellnessCalculationResult(
        sessions_per_week=3,
        minutes_per_session=45,
        weekly_available_minutes=135,
        non_training_days_per_week=4,
    )


def test_accepts_schema_valid_plan_with_matching_schedule_and_conservative_guidance() -> None:
    result = assess_generated_plan_safety(
        GeneratedPlan.model_validate(valid_plan_payload()),
        calculations(),
    )

    assert result.is_eligible is True
    assert result.issues == ()


def test_rejects_schedule_that_exceeds_deterministic_availability() -> None:
    payload = valid_plan_payload()
    workout_plan = payload["workout_plan"]
    assert isinstance(workout_plan, dict)
    sessions = workout_plan["sessions"]
    assert isinstance(sessions, list)
    sessions.pop()
    first_session = sessions[0]
    assert isinstance(first_session, dict)
    first_session["duration_minutes"] = 60

    result = assess_generated_plan_safety(GeneratedPlan.model_validate(payload), calculations())

    assert result.issues == (
        GeneratedPlanSafetyIssueCode.SESSION_COUNT_MISMATCH,
        GeneratedPlanSafetyIssueCode.SESSION_DURATION_EXCEEDED,
    )


def test_rejects_unsupported_or_unsafe_generated_guidance() -> None:
    payload = deepcopy(valid_plan_payload())
    nutrition_plan = payload["nutrition_plan"]
    workout_plan = payload["workout_plan"]
    assert isinstance(nutrition_plan, dict)
    assert isinstance(workout_plan, dict)
    nutrition_plan["summary"] = "Eat exactly 1,500 calories and take creatine."
    workout_plan["progression_guidance"] = "Push through the pain as physical therapy."

    result = assess_generated_plan_safety(GeneratedPlan.model_validate(payload), calculations())

    assert set(result.issues) == {
        GeneratedPlanSafetyIssueCode.MEDICAL_CONTENT,
        GeneratedPlanSafetyIssueCode.UNSUPPORTED_NUTRITION_TARGET,
        GeneratedPlanSafetyIssueCode.UNSAFE_PAIN_GUIDANCE,
        GeneratedPlanSafetyIssueCode.SUPPLEMENT_OR_MEDICATION_DIRECTIVE,
    }
