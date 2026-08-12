from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings

type DatabaseSessionFactory = sessionmaker[Session]


def create_database_engine(settings: Settings) -> Engine:
    """Create the application's synchronous SQLAlchemy connection pool."""
    return create_engine(
        str(settings.database_url),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


def verify_database_connection(engine: Engine) -> None:
    """Fail fast when PostgreSQL cannot serve a basic query."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def create_database_session_factory(engine: Engine) -> DatabaseSessionFactory:
    """Create sessions bound to the application engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_database_session(request: Request) -> Generator[Session]:
    """Provide one transaction-scoped SQLAlchemy session for a request."""
    factory: DatabaseSessionFactory = request.app.state.database_session_factory
    database_session = factory()

    try:
        yield database_session
        database_session.commit()
    except BaseException:
        database_session.rollback()
        raise
    finally:
        database_session.close()


# Function scope completes commit or rollback before FastAPI sends the response.
DatabaseSession = Annotated[Session, Depends(get_database_session, scope="function")]
