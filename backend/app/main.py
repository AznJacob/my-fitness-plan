import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.config import load_settings
from app.database import (
    create_database_engine,
    create_database_session_factory,
    verify_database_connection,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Own the database engine for the lifetime of the FastAPI application."""
    settings = load_settings()
    engine = create_database_engine(settings)

    try:
        verify_database_connection(engine)
    except SQLAlchemyError:
        engine.dispose()
        logger.exception("PostgreSQL connectivity check failed during application startup")
        raise

    database_session_factory = create_database_session_factory(engine)
    application.state.database_engine = engine
    application.state.database_session_factory = database_session_factory

    try:
        yield
    finally:
        engine.dispose()
        del application.state.database_session_factory
        del application.state.database_engine


app = FastAPI(title="MyFitnessPlan Backend", lifespan=lifespan)


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="my-fitness-plan-backend")
