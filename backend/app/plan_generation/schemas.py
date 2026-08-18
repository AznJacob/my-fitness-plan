from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.plan_generation.preferences import PlanningPreferences
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

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class LegacyExercisePrescription(StrictPlanModel):
    name: ShortText
    sets: int | None = Field(ge=1, le=10)
    repetitions: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=40)]
    duration_seconds: int | None = Field(ge=10, le=7_200)
    rest_seconds: int = Field(ge=0, le=600)
    instructions: DescriptionText

    @model_validator(mode="after")
    def require_repetitions_or_duration(self) -> LegacyExercisePrescription:
        if self.repetitions is None and self.duration_seconds is None:
            raise ValueError("An exercise must specify repetitions or duration seconds.")
        return self


class LegacyWorkoutSession(StrictPlanModel):
    day_label: ShortText
    focus: ShortText
    duration_minutes: int = Field(ge=10, le=180)
    warm_up: list[LegacyExercisePrescription] = Field(min_length=1, max_length=6)
    main_workout: list[LegacyExercisePrescription] = Field(min_length=1, max_length=12)
    cool_down: list[LegacyExercisePrescription] = Field(min_length=1, max_length=6)


class LegacyWorkoutPlan(StrictPlanModel):
    summary: DescriptionText
    sessions: list[LegacyWorkoutSession] = Field(min_length=1, max_length=7)
    progression_guidance: InstructionText
    recovery_guidance: InstructionText


class LegacyMealSuggestion(StrictPlanModel):
    meal_name: ShortText
    foods: list[ShortText] = Field(min_length=1, max_length=12)
    guidance: DescriptionText


class LegacyDailyNutritionTemplate(StrictPlanModel):
    day_label: ShortText
    meals: list[LegacyMealSuggestion] = Field(min_length=2, max_length=6)


class LegacyNutritionPlan(StrictPlanModel):
    summary: DescriptionText
    daily_templates: list[LegacyDailyNutritionTemplate] = Field(min_length=1, max_length=7)
    hydration_guidance: DescriptionText
    meal_timing_guidance: DescriptionText
    dietary_preference_notes: DescriptionText


class LegacyGeneratedPlan(StrictPlanModel):
    schema_version: Literal[1] = Field(alias="v")
    title: ShortText
    overview: DescriptionText
    workout_plan: LegacyWorkoutPlan
    nutrition_plan: LegacyNutritionPlan


class ExercisePrescription(StrictPlanModel):
    """Compact exercise direction suitable for a short generated plan."""

    name: ShortText = Field(alias="n")
    prescription: ShortText = Field(alias="p")


class WorkoutSession(StrictPlanModel):
    day_label: ShortText = Field(alias="d")
    focus: ShortText = Field(alias="f")
    duration_minutes: int = Field(ge=10, le=180, alias="m")
    exercises: list[ExercisePrescription] = Field(min_length=2, max_length=3, alias="e")


class WorkoutPlan(StrictPlanModel):
    sessions: list[WorkoutSession] = Field(min_length=1, max_length=7, alias="s")
    progression_guidance: DescriptionText = Field(alias="p")
    recovery_guidance: DescriptionText = Field(alias="r")


class MealSuggestion(StrictPlanModel):
    meal_name: ShortText = Field(alias="n")
    foods: list[ShortText] = Field(min_length=2, max_length=5, alias="f")


class NutritionPlan(StrictPlanModel):
    meal_ideas: list[MealSuggestion] = Field(min_length=3, max_length=3, alias="m")
    daily_guidance: DescriptionText = Field(alias="d")
    hydration_guidance: DescriptionText = Field(alias="h")


class GeneratedPlan(StrictPlanModel):
    """Version 2 output intentionally bounded for fast, concise generation."""

    schema_version: Literal[2] = Field(alias="v")
    title: ShortText = Field(alias="t")
    overview: DescriptionText = Field(alias="o")
    workout_plan: WorkoutPlan = Field(alias="w")
    nutrition_plan: NutritionPlan = Field(alias="n")


class ClaudePlanRequest(BaseModel):
    """Named prompt sections kept distinct before provider serialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    system_instructions: PromptSection
    application_context: PromptSection
    calculated_values: WellnessCalculationResult
    profile_data: PlanningPreferences
