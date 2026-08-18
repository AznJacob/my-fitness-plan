from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class AccountDetailsInput(BaseModel):
    username: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ] = None
    height_cm: Decimal | None = Field(default=None, ge=50, le=260, decimal_places=1)
    weight_kg: Decimal | None = Field(default=None, ge=20, le=400, decimal_places=1)


class AccountDetailsResponse(AccountDetailsInput):
    model_config = ConfigDict(from_attributes=True)
