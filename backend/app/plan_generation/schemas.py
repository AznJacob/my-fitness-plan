from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.profile.schemas import ProfileInput
from app.wellness.schemas import WellnessCalculationResult

ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
]
DescriptionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
InstructionText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1_000),
]
PromptSection = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4_000),
]


class StrictPlanModel(BaseModel):
    """Reject undeclared provider output instead of silently discarding it."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ExercisePrescription(StrictPlanModel):
    name: ShortText
    sets: int | None = Field(ge=1, le=10)
    repetitions: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=40)]
    duration_seconds: int | None = Field(ge=10, le=7_200)
    rest_seconds: int = Field(ge=0, le=600)
    instructions: DescriptionText

    @model_validator(mode="after")
    def require_repetitions_or_duration(self) -> ExercisePrescription:
        if self.repetitions is None and self.duration_seconds is None:
            raise ValueError("An exercise must specify repetitions or duration seconds.")
        return self


class WorkoutSession(StrictPlanModel):
    day_label: ShortText
    focus: ShortText
    duration_minutes: int = Field(ge=10, le=180)
    warm_up: list[ExercisePrescription] = Field(min_length=1, max_length=6)
    main_workout: list[ExercisePrescription] = Field(min_length=1, max_length=12)
    cool_down: list[ExercisePrescription] = Field(min_length=1, max_length=6)


class WorkoutPlan(StrictPlanModel):
    summary: DescriptionText
    sessions: list[WorkoutSession] = Field(min_length=1, max_length=7)
    progression_guidance: InstructionText
    recovery_guidance: InstructionText


class MealSuggestion(StrictPlanModel):
    meal_name: ShortText
    foods: list[ShortText] = Field(min_length=1, max_length=12)
    guidance: DescriptionText


class DailyNutritionTemplate(StrictPlanModel):
    day_label: ShortText
    meals: list[MealSuggestion] = Field(min_length=2, max_length=6)


class NutritionPlan(StrictPlanModel):
    summary: DescriptionText
    daily_templates: list[DailyNutritionTemplate] = Field(min_length=1, max_length=7)
    hydration_guidance: DescriptionText
    meal_timing_guidance: DescriptionText
    dietary_preference_notes: DescriptionText


class GeneratedPlan(StrictPlanModel):
    schema_version: Literal[1]
    title: ShortText
    overview: DescriptionText
    workout_plan: WorkoutPlan
    nutrition_plan: NutritionPlan


class ClaudePlanRequest(BaseModel):
    """Named prompt sections kept distinct before provider serialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    system_instructions: PromptSection
    application_context: PromptSection
    calculated_values: WellnessCalculationResult
    profile_data: ProfileInput
