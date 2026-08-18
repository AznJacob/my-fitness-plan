from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator


class FitnessGoal(StrEnum):
    GENERAL_FITNESS = "general_fitness"
    STRENGTH = "strength"
    MUSCLE_GAIN = "muscle_gain"
    ENDURANCE = "endurance"
    WEIGHT_MANAGEMENT = "weight_management"


class ExperienceLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


PreferenceListItem = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class PlanningPreferences(BaseModel):
    """Validated, per-request plan inputs that are not stored as account state."""

    fitness_goal: FitnessGoal
    experience_level: ExperienceLevel
    days_per_week: int = Field(ge=1, le=7)
    session_minutes: int = Field(ge=10, le=180)
    equipment: list[PreferenceListItem] = Field(default_factory=list, max_length=20)
    dietary_preferences: list[PreferenceListItem] = Field(default_factory=list, max_length=20)
    wellness_constraints: list[PreferenceListItem] = Field(default_factory=list, max_length=20)

    @field_validator("equipment", "dietary_preferences", "wellness_constraints")
    @classmethod
    def reject_duplicate_items(cls, values: list[str]) -> list[str]:
        normalized_values = [value.casefold() for value in values]
        if len(normalized_values) != len(set(normalized_values)):
            raise ValueError("List items must be unique.")
        return values
