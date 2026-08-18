from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Plan, User
from app.plan_generation.schemas import GeneratedPlan, NutritionPlan, WorkoutPlan
from app.plan_generation.workflow import GeneratedPlanResult
from app.plans.errors import ArchivedPlanActivationError, PlanNotFoundError
from app.plans.schemas import PlanDetail, PlanProfileSnapshot, PlanStatus, PlanSummary


def persist_generated_plan(
    database_session: Session,
    user: User,
    result: GeneratedPlanResult,
) -> PlanDetail:
    """Persist only the already validated plan and its exact generation inputs."""
    plan = GeneratedPlan.model_validate(result.plan.model_dump(mode="python"))
    snapshot = PlanProfileSnapshot(
        profile=result.profile,
        calculated_values=result.calculated_values,
    )
    stored_plan = Plan(
        user_id=user.id,
        title=plan.title,
        overview=plan.overview,
        status=PlanStatus.INACTIVE.value,
        schema_version=plan.schema_version,
        profile_snapshot=snapshot.model_dump(mode="json"),
        workout_plan=plan.workout_plan.model_dump(mode="json"),
        nutrition_plan=plan.nutrition_plan.model_dump(mode="json"),
    )
    database_session.add(stored_plan)
    database_session.flush()
    return plan_detail(stored_plan)


def list_plans(database_session: Session, user: User) -> list[PlanSummary]:
    plans = database_session.scalars(
        select(Plan).where(Plan.user_id == user.id).order_by(Plan.created_at.desc(), Plan.id.desc())
    ).all()
    return [plan_summary(plan) for plan in plans]


def get_plan_detail(database_session: Session, user: User, plan_id: UUID) -> PlanDetail:
    return plan_detail(_get_owned_plan(database_session, user, plan_id))


def activate_plan(database_session: Session, user: User, plan_id: UUID) -> PlanDetail:
    """Serialize active-plan changes per user and preserve the single-active invariant."""
    _lock_user(database_session, user)
    plan = _get_owned_plan(database_session, user, plan_id, for_update=True)
    if plan.status == PlanStatus.ARCHIVED.value:
        raise ArchivedPlanActivationError

    database_session.execute(
        update(Plan)
        .where(
            Plan.user_id == user.id,
            Plan.status == PlanStatus.ACTIVE.value,
            Plan.id != plan.id,
        )
        .values(status=PlanStatus.INACTIVE.value)
    )
    plan.status = PlanStatus.ACTIVE.value
    plan.archived_at = None
    database_session.flush()
    return plan_detail(plan)


def archive_plan(database_session: Session, user: User, plan_id: UUID) -> PlanDetail:
    """Archive an owned plan; archived plans are retained but cannot be reactivated."""
    _lock_user(database_session, user)
    plan = _get_owned_plan(database_session, user, plan_id, for_update=True)
    if plan.status != PlanStatus.ARCHIVED.value:
        plan.status = PlanStatus.ARCHIVED.value
        plan.archived_at = datetime.now(UTC)
        database_session.flush()
    return plan_detail(plan)


def plan_summary(plan: Plan) -> PlanSummary:
    return PlanSummary(
        id=plan.id,
        title=plan.title,
        status=PlanStatus(plan.status),
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        archived_at=plan.archived_at,
    )


def plan_detail(plan: Plan) -> PlanDetail:
    generated_plan = GeneratedPlan.model_validate(
        {
            "schema_version": plan.schema_version,
            "title": plan.title,
            "overview": plan.overview,
            "workout_plan": WorkoutPlan.model_validate(plan.workout_plan),
            "nutrition_plan": NutritionPlan.model_validate(plan.nutrition_plan),
        }
    )
    return PlanDetail(
        **generated_plan.model_dump(mode="python"),
        id=plan.id,
        status=PlanStatus(plan.status),
        profile_snapshot=PlanProfileSnapshot.model_validate(plan.profile_snapshot),
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        archived_at=plan.archived_at,
    )


def _get_owned_plan(
    database_session: Session,
    user: User,
    plan_id: UUID,
    *,
    for_update: bool = False,
) -> Plan:
    statement = select(Plan).where(Plan.id == plan_id, Plan.user_id == user.id)
    if for_update:
        statement = statement.with_for_update()
    plan = database_session.scalar(statement)
    if plan is None:
        raise PlanNotFoundError
    return plan


def _lock_user(database_session: Session, user: User) -> None:
    database_session.execute(
        select(User.id).where(User.id == user.id).with_for_update()
    ).scalar_one()
