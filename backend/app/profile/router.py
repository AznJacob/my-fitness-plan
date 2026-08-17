from fastapi import APIRouter, HTTPException, status

from app.auth.dependencies import AuthenticatedCsrfSession, CurrentUser
from app.database import DatabaseSession
from app.profile.schemas import ProfileInput, ProfileResponse
from app.profile.service import get_profile, save_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def read_profile(user: CurrentUser, database_session: DatabaseSession) -> ProfileResponse:
    profile = get_profile(database_session, user)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )
    return ProfileResponse.model_validate(profile)


@router.put("", response_model=ProfileResponse)
def replace_profile(
    payload: ProfileInput,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedCsrfSession,
) -> ProfileResponse:
    profile = save_profile(database_session, authenticated_session.user, payload)
    return ProfileResponse.model_validate(profile)
