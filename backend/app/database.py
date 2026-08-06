from sqlalchemy import Engine, create_engine, text

from app.config import Settings


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
