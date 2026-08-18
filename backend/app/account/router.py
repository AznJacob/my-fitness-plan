from fastapi import APIRouter, HTTPException, status

from app.account.schemas import AccountDetailsInput, AccountDetailsResponse
from app.account.service import get_account_details, save_account_details
from app.auth.dependencies import AuthenticatedCsrfSession, CurrentUser
from app.database import DatabaseSession

router = APIRouter(prefix="/account/details", tags=["account"])


@router.get("", response_model=AccountDetailsResponse)
def read_account_details(
    user: CurrentUser,
    database_session: DatabaseSession,
) -> AccountDetailsResponse:
    details = get_account_details(database_session, user)
    if details is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account details not found.",
        )
    return AccountDetailsResponse.model_validate(details)


@router.put("", response_model=AccountDetailsResponse)
def replace_account_details(
    payload: AccountDetailsInput,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedCsrfSession,
) -> AccountDetailsResponse:
    details = save_account_details(database_session, authenticated_session.user, payload)
    return AccountDetailsResponse.model_validate(details)
