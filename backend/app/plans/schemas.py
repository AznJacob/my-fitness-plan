from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.plan_generation.schemas import GeneratedPlan, LegacyGeneratedPlan
from app.profile.schemas import ProfileInput
from app.wellness.schemas import WellnessCalculationResult


class PlanStatus(StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    ARCHIVED = "archived"


class PlanProfileSnapshot(BaseModel):
    """Immutable generation inputs retained with a validated plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile: ProfileInput
    calculated_values: WellnessCalculationResult


class PlanSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    title: str
    status: PlanStatus
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class PlanDetail(GeneratedPlan):
    """Lifecycle metadata plus the complete schema-validated generated plan."""

    id: UUID
    status: PlanStatus
    profile_snapshot: PlanProfileSnapshot
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class LegacyPlanDetail(LegacyGeneratedPlan):
    """Readable lifecycle representation for schema-version-1 plans."""

    id: UUID
    status: PlanStatus
    profile_snapshot: PlanProfileSnapshot
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


PersistedPlanDetail = Annotated[
    PlanDetail | LegacyPlanDetail,
    Field(discriminator="schema_version"),
]
