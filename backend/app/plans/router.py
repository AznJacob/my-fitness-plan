from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.auth.dependencies import AuthenticatedCsrfSession, CurrentUser
from app.database import DatabaseSession
from app.plans.errors import ArchivedPlanActivationError, PlanNotFoundError
from app.plans.schemas import PersistedPlanDetail, PlanSummary
from app.plans.service import activate_plan, archive_plan, get_plan_detail, list_plans

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanSummary])
def read_plan_history(user: CurrentUser, database_session: DatabaseSession) -> list[PlanSummary]:
    return list_plans(database_session, user)


@router.get("/{plan_id}", response_model=PersistedPlanDetail, response_model_by_alias=False)
def read_plan(
    plan_id: UUID,
    user: CurrentUser,
    database_session: DatabaseSession,
) -> PersistedPlanDetail:
    try:
        return get_plan_detail(database_session, user, plan_id)
    except PlanNotFoundError as error:
        raise _not_found() from error


@router.post(
    "/{plan_id}/activate",
    response_model=PersistedPlanDetail,
    response_model_by_alias=False,
)
def select_active_plan(
    plan_id: UUID,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedCsrfSession,
) -> PersistedPlanDetail:
    try:
        return activate_plan(database_session, authenticated_session.user, plan_id)
    except PlanNotFoundError as error:
        raise _not_found() from error
    except ArchivedPlanActivationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "archived_plan",
                "message": "Archived plans cannot be selected as active.",
            },
        ) from error


@router.post(
    "/{plan_id}/archive",
    response_model=PersistedPlanDetail,
    response_model_by_alias=False,
)
def archive_owned_plan(
    plan_id: UUID,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedCsrfSession,
) -> PersistedPlanDetail:
    try:
        return archive_plan(database_session, authenticated_session.user, plan_id)
    except PlanNotFoundError as error:
        raise _not_found() from error


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "plan_not_found", "message": "Plan not found."},
    )
