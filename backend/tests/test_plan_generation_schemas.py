from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.plan_generation.schemas import ClaudePlanRequest, GeneratedPlan
from app.profile.schemas import ProfileInput
from app.wellness.service import calculate_profile_wellness


def valid_profile() -> ProfileInput:
    return ProfileInput.model_validate(
        {
            "display_name": "Jordan",
            "fitness_goal": "general_fitness",
            "experience_level": "beginner",
            "days_per_week": 3,
            "session_minutes": 45,
            "equipment": ["Dumbbells"],
            "dietary_preferences": ["Vegetarian"],
            "wellness_constraints": ["Prefer low-impact movements"],
        }
    )


def valid_generated_plan() -> dict[str, object]:
    exercise = {
        "name": "Bodyweight squat",
        "sets": 3,
        "repetitions": "8-10",
        "duration_seconds": None,
        "rest_seconds": 60,
        "instructions": "Use a comfortable range of motion and controlled tempo.",
    }
    return {
        "schema_version": 1,
        "title": "Three-day general fitness plan",
        "overview": "A balanced weekly routine using the available equipment.",
        "workout_plan": {
            "summary": "Three full-body sessions with gradual progression.",
            "sessions": [
                {
                    "day_label": "Day 1",
                    "focus": "Full body",
                    "duration_minutes": 45,
                    "warm_up": [exercise],
                    "main_workout": [exercise],
                    "cool_down": [exercise],
                }
            ],
            "progression_guidance": "Add repetitions before increasing resistance.",
            "recovery_guidance": "Leave time between sessions and adjust effort as needed.",
        },
        "nutrition_plan": {
            "summary": "Flexible vegetarian meal suggestions using varied whole foods.",
            "daily_templates": [
                {
                    "day_label": "Training day",
                    "meals": [
                        {
                            "meal_name": "Breakfast",
                            "foods": ["Oats", "Fruit", "Yogurt"],
                            "guidance": "Choose portions based on appetite.",
                        },
                        {
                            "meal_name": "Dinner",
                            "foods": ["Lentils", "Rice", "Vegetables"],
                            "guidance": "Include a variety of vegetables.",
                        },
                    ],
                }
            ],
            "hydration_guidance": "Drink regularly and adjust for heat and activity.",
            "meal_timing_guidance": "Use meal timing that fits the daily schedule.",
            "dietary_preference_notes": "All suggestions are vegetarian.",
        },
    }


def test_generated_plan_accepts_complete_bounded_output() -> None:
    plan = GeneratedPlan.model_validate(valid_generated_plan())

    assert plan.schema_version == 1
    assert plan.workout_plan.sessions[0].duration_minutes == 45
    assert plan.nutrition_plan.daily_templates[0].meals[0].foods[0] == "Oats"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda plan: plan.update({"unexpected": "value"}),
        lambda plan: plan.update({"schema_version": 2}),
        lambda plan: plan["workout_plan"].update({"sessions": []}),
        lambda plan: plan["nutrition_plan"].update({"daily_templates": []}),
    ],
)
def test_generated_plan_rejects_extra_versioned_or_empty_output(mutate: object) -> None:
    payload = deepcopy(valid_generated_plan())
    mutate(payload)  # type: ignore[operator]

    with pytest.raises(ValidationError):
        GeneratedPlan.model_validate(payload)


def test_exercise_requires_repetitions_or_duration() -> None:
    payload = valid_generated_plan()
    exercise = payload["workout_plan"]["sessions"][0]["main_workout"][0]  # type: ignore[index]
    exercise["repetitions"] = None
    exercise["duration_seconds"] = None

    with pytest.raises(ValidationError, match="repetitions or duration"):
        GeneratedPlan.model_validate(payload)


def test_prompt_sections_remain_named_and_separate() -> None:
    profile = valid_profile()
    request = ClaudePlanRequest(
        system_instructions="Follow the general-wellness safety boundary.",
        application_context="Create a workout and nutrition plan using only supplied facts.",
        calculated_values=calculate_profile_wellness(profile),
        profile_data=profile,
    )

    assert request.system_instructions.startswith("Follow")
    assert request.application_context.startswith("Create")
    assert request.calculated_values.weekly_available_minutes == 135
    assert request.profile_data.wellness_constraints == ["Prefer low-impact movements"]
