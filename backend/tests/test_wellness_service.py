import pytest

from app.plan_generation.preferences import PlanningPreferences as ProfileInput
from app.wellness.schemas import (
    WellnessCalculationInput,
    WellnessSafetyInput,
    WellnessSafetyIssueCode,
)
from app.wellness.service import (
    assess_preferences_safety as assess_profile_safety,
)
from app.wellness.service import (
    assess_wellness_safety,
    calculate_wellness,
)
from app.wellness.service import (
    calculate_preferences_wellness as calculate_profile_wellness,
)


def valid_profile(**overrides: object) -> ProfileInput:
    values: dict[str, object] = {
        "display_name": "Jordan",
        "fitness_goal": "general_fitness",
        "experience_level": "beginner",
        "days_per_week": 3,
        "session_minutes": 45,
        "equipment": ["Dumbbells"],
        "dietary_preferences": ["Vegetarian"],
        "wellness_constraints": ["Prefer low-impact movements"],
    }
    values.update(overrides)
    return ProfileInput.model_validate(values)


@pytest.mark.parametrize(
    ("days_per_week", "session_minutes", "weekly_minutes", "non_training_days"),
    [
        (1, 10, 10, 6),
        (3, 45, 135, 4),
        (7, 180, 1_260, 0),
    ],
)
def test_calculate_wellness_uses_whole_minutes_and_seven_day_weeks(
    days_per_week: int,
    session_minutes: int,
    weekly_minutes: int,
    non_training_days: int,
) -> None:
    result = calculate_wellness(
        WellnessCalculationInput(
            days_per_week=days_per_week,
            session_minutes=session_minutes,
        )
    )

    assert result.sessions_per_week == days_per_week
    assert result.minutes_per_session == session_minutes
    assert result.weekly_available_minutes == weekly_minutes
    assert result.non_training_days_per_week == non_training_days


def test_calculate_profile_wellness_uses_only_supported_profile_fields() -> None:
    result = calculate_profile_wellness(
        valid_profile(
            fitness_goal="strength",
            experience_level="advanced",
            days_per_week=4,
            session_minutes=60,
            dietary_preferences=["Vegan"],
        )
    )

    assert result.weekly_available_minutes == 240
    assert result.non_training_days_per_week == 3


def test_general_wellness_preferences_remain_eligible() -> None:
    result = assess_profile_safety(
        valid_profile(
            wellness_constraints=[
                "Prefer low-impact movements",
                "Focus on injury prevention",
            ]
        )
    )

    assert result.is_eligible is True
    assert result.issues == ()


@pytest.mark.parametrize(
    "constraint",
    [
        "Build a rehabilitation plan for my knee",
        "I need physical therapy exercises",
        "Treat my shoulder problem",
        "Recovering from surgery",
        "Create workouts for pregnancy",
        "Help manage an eating disorder",
        "Plan around my medical condition",
        "Train my injured ankle",
        "I need an INJURY program",
    ],
)
def test_explicit_medical_or_rehabilitation_requests_are_ineligible(constraint: str) -> None:
    result = assess_profile_safety(valid_profile(wellness_constraints=[constraint]))

    assert result.is_eligible is False
    assert [issue.code for issue in result.issues] == [
        WellnessSafetyIssueCode.MEDICAL_OR_REHABILITATION_REQUEST
    ]


@pytest.mark.parametrize("session_minutes", [1, 9, 181, 1_440])
def test_duration_outside_planning_scope_is_ineligible(session_minutes: int) -> None:
    result = assess_wellness_safety(
        WellnessSafetyInput(
            session_minutes=session_minutes,
            wellness_constraints=(),
        )
    )

    assert result.is_eligible is False
    assert [issue.code for issue in result.issues] == [
        WellnessSafetyIssueCode.SESSION_DURATION_OUT_OF_SCOPE
    ]


def test_safety_assessment_reports_each_distinct_issue_once() -> None:
    result = assess_wellness_safety(
        WellnessSafetyInput(
            session_minutes=181,
            wellness_constraints=("Rehabilitation", "Treat an injury"),
        )
    )

    assert result.is_eligible is False
    assert [issue.code for issue in result.issues] == [
        WellnessSafetyIssueCode.SESSION_DURATION_OUT_OF_SCOPE,
        WellnessSafetyIssueCode.MEDICAL_OR_REHABILITATION_REQUEST,
    ]
