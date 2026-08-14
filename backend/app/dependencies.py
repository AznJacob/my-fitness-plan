from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings


def get_application_settings(request: Request) -> Settings:
    """Return the settings validated once during application startup."""
    settings: Settings = request.app.state.settings
    return settings


ApplicationSettings = Annotated[Settings, Depends(get_application_settings)]
