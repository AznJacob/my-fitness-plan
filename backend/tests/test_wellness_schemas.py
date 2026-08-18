import pytest
from pydantic import ValidationError

from app.wellness.schemas import (
    WellnessCalculationInput,
    WellnessCalculationResult,
    WellnessSafetyIssue,
    WellnessSafetyIssueCode,
    WellnessSafetyResult,
)


def test_calculation_input_accepts_only_supported_schedule_bounds() -> None:
    assert WellnessCalculationInput(days_per_week=1, session_minutes=10).model_dump() == {
        "days_per_week": 1,
        "session_minutes": 10,
    }
    assert WellnessCalculationInput(days_per_week=7, session_minutes=180).model_dump() == {
        "days_per_week": 7,
        "session_minutes": 180,
    }

    for payload in (
        {"days_per_week": 0, "session_minutes": 45},
        {"days_per_week": 8, "session_minutes": 45},
        {"days_per_week": 3, "session_minutes": 9},
        {"days_per_week": 3, "session_minutes": 181},
        {"days_per_week": "3", "session_minutes": 45},
    ):
        with pytest.raises(ValidationError):
            WellnessCalculationInput.model_validate(payload)


def test_calculation_result_enforces_declared_formulas() -> None:
    result = WellnessCalculationResult(
        sessions_per_week=3,
        minutes_per_session=45,
        weekly_available_minutes=135,
        non_training_days_per_week=4,
    )

    assert result.calculation_version == 1

    with pytest.raises(ValidationError, match="Weekly available minutes"):
        WellnessCalculationResult(
            sessions_per_week=3,
            minutes_per_session=45,
            weekly_available_minutes=134,
            non_training_days_per_week=4,
        )

    with pytest.raises(ValidationError, match="Non-training days"):
        WellnessCalculationResult(
            sessions_per_week=3,
            minutes_per_session=45,
            weekly_available_minutes=135,
            non_training_days_per_week=3,
        )


def test_safety_result_requires_issues_exactly_when_ineligible() -> None:
    issue = WellnessSafetyIssue(
        code=WellnessSafetyIssueCode.MEDICAL_OR_REHABILITATION_REQUEST,
        field="wellness_constraints",
        message="This request is outside the application's general-wellness scope.",
    )

    assert WellnessSafetyResult(is_eligible=True, issues=()).issues == ()
    assert WellnessSafetyResult(is_eligible=False, issues=(issue,)).issues == (issue,)

    with pytest.raises(ValidationError, match="Eligibility"):
        WellnessSafetyResult(is_eligible=True, issues=(issue,))
