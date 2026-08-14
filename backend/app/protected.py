from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.dependencies import CurrentUser

router = APIRouter(tags=["protected example"])


class ProtectedResponse(BaseModel):
    message: str
    user_id: UUID


@router.get("/protected", response_model=ProtectedResponse)
def protected_example(user: CurrentUser) -> ProtectedResponse:
    """Demonstrate authentication without introducing future resource authorization."""
    return ProtectedResponse(message="You are authenticated.", user_id=user.id)
