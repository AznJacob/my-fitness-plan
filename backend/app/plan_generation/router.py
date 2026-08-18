from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.auth.dependencies import AuthenticatedCsrfSession
from app.database import DatabaseSession
from app.dependencies import ApplicationSettings
from app.plan_generation.errors import (
    PlanGenerationError,
    PlanGenerationFailureCode,
    PlanWorkflowError,
    PlanWorkflowFailureCode,
)
from app.plan_generation.workflow import generate_plan_result_for_user
from app.plans.schemas import PlanDetail
from app.plans.service import persist_generated_plan

router = APIRouter(prefix="/plans", tags=["plans"])

_INVALID_OUTPUT_FAILURES = {
    PlanGenerationFailureCode.EMPTY_OUTPUT,
    PlanGenerationFailureCode.INVALID_JSON,
    PlanGenerationFailureCode.SCHEMA_VIOLATION,
    PlanGenerationFailureCode.OUTPUT_TRUNCATED,
    PlanGenerationFailureCode.UNEXPECTED_RESPONSE,
}
_WORKFLOW_STATUS_CODES = {
    PlanWorkflowFailureCode.MISSING_PROFILE: status.HTTP_404_NOT_FOUND,
    PlanWorkflowFailureCode.UNSAFE_PROFILE: status.HTTP_422_UNPROCESSABLE_CONTENT,
    PlanWorkflowFailureCode.UNSAFE_MODEL_OUTPUT: status.HTTP_502_BAD_GATEWAY,
}


@router.post(
    "/generate",
    response_model=PlanDetail,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
def generate_plan(
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedCsrfSession,
    settings: ApplicationSettings,
) -> PlanDetail:
    """Generate, validate, and persist a plan for the authenticated user."""
    try:
        result = generate_plan_result_for_user(
            database_session,
            authenticated_session.user,
            settings,
        )
        return persist_generated_plan(database_session, authenticated_session.user, result)
    except PlanWorkflowError as error:
        raise HTTPException(
            status_code=_WORKFLOW_STATUS_CODES[error.code],
            detail=_error_detail(error.code.value, error.public_message, error.issues),
        ) from error
    except PlanGenerationError as error:
        raise _provider_http_error(error) from error


def _provider_http_error(error: PlanGenerationError) -> HTTPException:
    if error.code is PlanGenerationFailureCode.MISSING_CONFIGURATION:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_error_detail("claude_unavailable", error.public_message),
        )
    if error.code in {
        PlanGenerationFailureCode.TIMEOUT,
        PlanGenerationFailureCode.NETWORK_FAILURE,
    }:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_error_detail("provider_unavailable", error.public_message),
        )
    if error.code in _INVALID_OUTPUT_FAILURES:
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_error_detail("invalid_model_output", error.public_message),
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=_error_detail("provider_failure", error.public_message),
    )


def _error_detail(code: str, message: str, issues: tuple[str, ...] = ()) -> dict[str, Any]:
    detail: dict[str, Any] = {"code": code, "message": message}
    if issues:
        detail["issues"] = list(issues)
    return detail
