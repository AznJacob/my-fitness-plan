import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.account.router import router as account_router
from app.auth.router import router as authentication_router
from app.config import LOCAL_FRONTEND_ORIGINS, load_settings
from app.database import (
    create_database_engine,
    create_database_session_factory,
    verify_database_connection,
)
from app.middleware import NoStoreMiddleware
from app.plan_generation.router import router as plan_generation_router
from app.plans.router import router as plans_router
from app.protected import router as protected_router

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
    application.state.settings = settings
    application.state.database_engine = engine
    application.state.database_session_factory = database_session_factory

    try:
        yield
    finally:
        engine.dispose()
        del application.state.database_session_factory
        del application.state.database_engine
        del application.state.settings


app = FastAPI(title="MyFitnessPlan Backend", lifespan=lifespan)
app.add_middleware(NoStoreMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(LOCAL_FRONTEND_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.include_router(authentication_router)
app.include_router(account_router)
app.include_router(plan_generation_router)
app.include_router(plans_router)
app.include_router(protected_router)


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="my-fitness-plan-backend")
