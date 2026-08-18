from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MIN_SESSION_MINUTES = 10
MAX_SESSION_MINUTES = 180
MAX_WEEKLY_AVAILABLE_MINUTES = 7 * MAX_SESSION_MINUTES
SafetyConstraint = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class WellnessCalculationInput(BaseModel):
    """Profile values that support exact, non-physiological calculations."""

    model_config = ConfigDict(extra="forbid")

    days_per_week: int = Field(strict=True, ge=1, le=7)
    session_minutes: int = Field(
        strict=True,
        ge=MIN_SESSION_MINUTES,
        le=MAX_SESSION_MINUTES,
    )


class WellnessCalculationResult(BaseModel):
    """Versioned schedule facts derived deterministically from request preferences."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    calculation_version: Literal[1] = 1
    sessions_per_week: int = Field(strict=True, ge=1, le=7)
    minutes_per_session: int = Field(
        strict=True,
        ge=MIN_SESSION_MINUTES,
        le=MAX_SESSION_MINUTES,
    )
    weekly_available_minutes: int = Field(
        strict=True,
        ge=MIN_SESSION_MINUTES,
        le=MAX_WEEKLY_AVAILABLE_MINUTES,
    )
    non_training_days_per_week: int = Field(strict=True, ge=0, le=6)

    @model_validator(mode="after")
    def derived_values_match_inputs(self) -> WellnessCalculationResult:
        if self.weekly_available_minutes != self.sessions_per_week * self.minutes_per_session:
            raise ValueError("Weekly available minutes must equal sessions times session minutes.")
        if self.non_training_days_per_week != 7 - self.sessions_per_week:
            raise ValueError("Non-training days must equal seven minus sessions per week.")
        return self


class WellnessSafetyIssueCode(StrEnum):
    SESSION_DURATION_OUT_OF_SCOPE = "session_duration_out_of_scope"
    MEDICAL_OR_REHABILITATION_REQUEST = "medical_or_rehabilitation_request"


class WellnessSafetyInput(BaseModel):
    """Bounded preference values used only to assess the generation scope."""

    model_config = ConfigDict(extra="forbid")

    session_minutes: int = Field(strict=True, ge=1, le=1_440)
    wellness_constraints: tuple[SafetyConstraint, ...] = Field(max_length=20)


class WellnessSafetyIssue(BaseModel):
    """A stable machine-readable reason that plan generation cannot proceed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: WellnessSafetyIssueCode
    field: Literal["session_minutes", "wellness_constraints"]
    message: str = Field(min_length=1, max_length=300)


class WellnessSafetyResult(BaseModel):
    """Eligibility result kept separate from calculation values and future prompts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_eligible: bool
    issues: tuple[WellnessSafetyIssue, ...] = Field(max_length=10)

    @model_validator(mode="after")
    def eligibility_matches_issues(self) -> WellnessSafetyResult:
        if self.is_eligible == bool(self.issues):
            raise ValueError("Eligibility must be true exactly when there are no safety issues.")
        return self
