from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RegistrationRequest(BaseModel):
    email: str
    password: str = Field(repr=False)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(repr=False)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1, max_length=8192, repr=False)


class LinkGoogleRequest(BaseModel):
    password: str = Field(repr=False)
    id_token: str = Field(min_length=1, max_length=8192, repr=False)


class LinkPasswordRequest(BaseModel):
    new_password: str = Field(repr=False)
    google_id_token: str = Field(min_length=1, max_length=8192, repr=False)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str


class ConnectedMethodsResponse(BaseModel):
    password: bool
    google: bool
