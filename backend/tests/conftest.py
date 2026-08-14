from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

TEST_DATABASE_PREFIX = "myfitnessplan_test_"


@pytest.fixture
def empty_database_url() -> Iterator[str]:
    """Create a disposable empty PostgreSQL database and remove only that database."""
    admin_url_value = os.environ.get("TEST_DATABASE_ADMIN_URL")
    if admin_url_value is None:
        pytest.skip("TEST_DATABASE_ADMIN_URL is required for PostgreSQL integration tests")

    admin_url = make_url(admin_url_value)
    database_name = f"{TEST_DATABASE_PREFIX}{uuid4().hex}"
    assert len(database_name) <= 63
    assert database_name.replace("_", "").isalnum()

    quoted_database_name = f'"{database_name}"'
    test_database_url = admin_url.set(database=database_name)
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as connection:
        connection.exec_driver_sql(f"CREATE DATABASE {quoted_database_name}")

    try:
        yield test_database_url.render_as_string(hide_password=False)
    finally:
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database_name,),
            )
            connection.exec_driver_sql(f"DROP DATABASE {quoted_database_name}")
        admin_engine.dispose()
