from __future__ import annotations

import re
import unicodedata
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.plan_generation.schemas import GeneratedPlan
from app.wellness.schemas import WellnessCalculationResult


class GeneratedPlanSafetyIssueCode(StrEnum):
    SESSION_COUNT_MISMATCH = "session_count_mismatch"
    SESSION_DURATION_EXCEEDED = "session_duration_exceeded"
    MEDICAL_CONTENT = "medical_content"
    UNSUPPORTED_NUTRITION_TARGET = "unsupported_nutrition_target"
    UNSAFE_PAIN_GUIDANCE = "unsafe_pain_guidance"
    SUPPLEMENT_OR_MEDICATION_DIRECTIVE = "supplement_or_medication_directive"


class GeneratedPlanSafetyResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    is_eligible: bool
    issues: tuple[GeneratedPlanSafetyIssueCode, ...] = Field(max_length=10)

    @model_validator(mode="after")
    def eligibility_matches_issues(self) -> GeneratedPlanSafetyResult:
        if self.is_eligible == bool(self.issues):
            raise ValueError("Eligibility must be true exactly when there are no safety issues.")
        return self


_MEDICAL_CONTENT = re.compile(
    r"\b(?:diagnos(?:e|is)|cure|rehab(?:ilitat(?:e|ion|ing))?|physical therap(?:y|ist)|"
    r"physiotherap(?:y|ist)|treat(?:ment|ing)?|"
    r"post[- ]?(?:operative|surgery|surgical)|eating disorder)\b"
)
_NUTRITION_TARGET = re.compile(
    r"\b(?:\d[\d,]*(?:\.\d+)?\s*(?:kcal|calories?)|"
    r"\d+(?:\.\d+)?\s*(?:g|grams?)\s+(?:of\s+)?"
    r"(?:protein|carbohydrates?|carbs?|fat))\b"
)
_UNSAFE_PAIN_GUIDANCE = re.compile(r"\b(?:push through|ignore)(?:\s+(?:any|the))?\s+pain\b")
_SUPPLEMENT_OR_MEDICATION_DIRECTIVE = re.compile(
    r"\b(?:take|use|start)\s+(?:\d+(?:\.\d+)?\s*(?:mg|g)\s+)?"
    r"(?:a\s+)?(?:supplement|medication|creatine|pre-workout|fat burner)\b"
)


def assess_generated_plan_safety(
    plan: GeneratedPlan,
    calculated_values: WellnessCalculationResult,
) -> GeneratedPlanSafetyResult:
    """Apply deterministic scope checks after schema validation and before API release."""
    issues: list[GeneratedPlanSafetyIssueCode] = []
    sessions = plan.workout_plan.sessions

    if len(sessions) != calculated_values.sessions_per_week:
        issues.append(GeneratedPlanSafetyIssueCode.SESSION_COUNT_MISMATCH)
    if any(
        session.duration_minutes > calculated_values.minutes_per_session for session in sessions
    ):
        issues.append(GeneratedPlanSafetyIssueCode.SESSION_DURATION_EXCEEDED)

    normalized_text = " ".join(
        unicodedata.normalize("NFKC", value).casefold()
        for value in _iter_strings(plan.model_dump(mode="json"))
    )
    for pattern, code in (
        (_MEDICAL_CONTENT, GeneratedPlanSafetyIssueCode.MEDICAL_CONTENT),
        (_NUTRITION_TARGET, GeneratedPlanSafetyIssueCode.UNSUPPORTED_NUTRITION_TARGET),
        (_UNSAFE_PAIN_GUIDANCE, GeneratedPlanSafetyIssueCode.UNSAFE_PAIN_GUIDANCE),
        (
            _SUPPLEMENT_OR_MEDICATION_DIRECTIVE,
            GeneratedPlanSafetyIssueCode.SUPPLEMENT_OR_MEDICATION_DIRECTIVE,
        ),
    ):
        if pattern.search(normalized_text) is not None:
            issues.append(code)

    return GeneratedPlanSafetyResult(is_eligible=not issues, issues=tuple(issues))


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for nested in value.values() for item in _iter_strings(nested)]
    if isinstance(value, list):
        return [item for nested in value for item in _iter_strings(nested)]
    return []
