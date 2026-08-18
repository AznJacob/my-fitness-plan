from __future__ import annotations

import re
import unicodedata

from app.profile.schemas import ProfileInput
from app.wellness.schemas import (
    MAX_SESSION_MINUTES,
    MIN_SESSION_MINUTES,
    WellnessCalculationInput,
    WellnessCalculationResult,
    WellnessSafetyInput,
    WellnessSafetyIssue,
    WellnessSafetyIssueCode,
    WellnessSafetyResult,
)

_ALLOWED_GENERAL_WELLNESS_PHRASES = (
    "injury prevention",
    "prevent injury",
)
_OUT_OF_SCOPE_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\b(?:rehab(?:ilitat(?:e|ion|ing))?|physical therap(?:y|ist)|physiotherap(?:y|ist))\b",
        r"\b(?:diagnos(?:e|is)|treat(?:ment|ing)?|cure)\b",
        r"\b(?:recover(?:y|ing)?\s+from|post[- ]?(?:operative|surgery|surgical))\b",
        r"\b(?:pregnan(?:t|cy)|eating disorder)\b",
        r"\b(?:medical condition|disease)\b",
        r"\b(?:injury|injured)\b",
    )
)


def calculate_wellness(payload: WellnessCalculationInput) -> WellnessCalculationResult:
    """Derive exact schedule facts without making physiological recommendations."""
    return WellnessCalculationResult(
        sessions_per_week=payload.days_per_week,
        minutes_per_session=payload.session_minutes,
        weekly_available_minutes=payload.days_per_week * payload.session_minutes,
        non_training_days_per_week=7 - payload.days_per_week,
    )


def calculate_profile_wellness(profile: ProfileInput) -> WellnessCalculationResult:
    """Adapt a validated saved profile to the calculation-only contract."""
    return calculate_wellness(
        WellnessCalculationInput(
            days_per_week=profile.days_per_week,
            session_minutes=profile.session_minutes,
        )
    )


def assess_wellness_safety(payload: WellnessSafetyInput) -> WellnessSafetyResult:
    """Reject explicit requests outside the application's general-wellness scope."""
    issues: list[WellnessSafetyIssue] = []

    if not MIN_SESSION_MINUTES <= payload.session_minutes <= MAX_SESSION_MINUTES:
        issues.append(
            WellnessSafetyIssue(
                code=WellnessSafetyIssueCode.SESSION_DURATION_OUT_OF_SCOPE,
                field="session_minutes",
                message=(
                    f"Session duration must be between {MIN_SESSION_MINUTES} and "
                    f"{MAX_SESSION_MINUTES} minutes for this planning application."
                ),
            )
        )

    if any(_contains_out_of_scope_request(value) for value in payload.wellness_constraints):
        issues.append(
            WellnessSafetyIssue(
                code=WellnessSafetyIssueCode.MEDICAL_OR_REHABILITATION_REQUEST,
                field="wellness_constraints",
                message=(
                    "MyFitnessPlan cannot create plans for medical treatment, injury treatment, "
                    "pregnancy, eating disorders, or rehabilitation. Please consult an "
                    "appropriately qualified professional."
                ),
            )
        )

    return WellnessSafetyResult(is_eligible=not issues, issues=tuple(issues))


def assess_profile_safety(profile: ProfileInput) -> WellnessSafetyResult:
    """Adapt bounded profile fields to the safety-only contract."""
    return assess_wellness_safety(
        WellnessSafetyInput(
            session_minutes=profile.session_minutes,
            wellness_constraints=tuple(profile.wellness_constraints),
        )
    )


def _contains_out_of_scope_request(value: str) -> bool:
    normalized_value = unicodedata.normalize("NFKC", value).casefold()
    for allowed_phrase in _ALLOWED_GENERAL_WELLNESS_PHRASES:
        normalized_value = normalized_value.replace(allowed_phrase, " ")
    return any(pattern.search(normalized_value) is not None for pattern in _OUT_OF_SCOPE_PATTERNS)
