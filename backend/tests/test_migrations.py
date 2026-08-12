from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_HEAD = "b2f7c91d4e63"
TEST_DATABASE_PREFIX = "myfitnessplan_migration_test_"


@pytest.fixture
def empty_database_url() -> Iterator[str]:
    """Create a disposable empty database and remove only that database afterward."""
    admin_url_value = os.environ.get("TEST_DATABASE_ADMIN_URL")
    if admin_url_value is None:
        pytest.skip("TEST_DATABASE_ADMIN_URL is required for migration integration tests")

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


@pytest.mark.integration
def test_upgrade_head_builds_expected_schema_from_empty_database(
    empty_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", empty_database_url)
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    engine = create_engine(empty_database_url)

    try:
        assert inspect(engine).get_table_names() == []

        command.upgrade(alembic_config, "head")

        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == {
            "alembic_version",
            "authentication_identities",
            "plans",
            "profiles",
            "sessions",
            "users",
        }

        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == (MIGRATION_HEAD)

        for table_name in ("authentication_identities", "plans", "profiles", "sessions"):
            foreign_keys = inspector.get_foreign_keys(table_name)
            assert len(foreign_keys) == 1
            assert foreign_keys[0]["referred_table"] == "users"
            assert foreign_keys[0]["options"] == {"ondelete": "CASCADE"}

        identity_indexes = {
            index["name"]: index for index in inspector.get_indexes("authentication_identities")
        }
        assert identity_indexes["uq_authentication_identities_password_email"]["unique"] is True

        plan_indexes = {index["name"]: index for index in inspector.get_indexes("plans")}
        assert plan_indexes["uq_plans_one_active_per_user"]["unique"] is True

        user_columns = {column["name"]: column for column in inspector.get_columns("users")}
        assert user_columns["normalized_email"]["nullable"] is False
        user_unique_constraints = {
            constraint["name"] for constraint in inspector.get_unique_constraints("users")
        }
        assert "uq_users_normalized_email" in user_unique_constraints

        session_indexes = {index["name"]: index for index in inspector.get_indexes("sessions")}
        assert session_indexes["uq_sessions_token_hash"]["unique"] is True
        assert {"ix_sessions_user_id", "ix_sessions_expires_at"} <= session_indexes.keys()

        session_checks = {
            constraint["name"] for constraint in inspector.get_check_constraints("sessions")
        }
        assert {
            "ck_sessions_token_hash_length",
            "ck_sessions_csrf_token_hash_length",
            "ck_sessions_expiration",
            "ck_sessions_revocation",
        } <= session_checks
    finally:
        engine.dispose()

    command.check(alembic_config)


@pytest.mark.integration
def test_session_migration_backfills_canonical_email_for_existing_user(
    empty_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", empty_database_url)
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    engine = create_engine(empty_database_url)
    user_id = uuid4()
    identity_id = uuid4()

    try:
        command.upgrade(alembic_config, "7768cfd3a397")

        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO users (id) VALUES (:user_id)"), {"user_id": user_id}
            )
            connection.execute(
                text(
                    """
                    INSERT INTO authentication_identities (
                        id,
                        user_id,
                        provider,
                        provider_subject,
                        email,
                        normalized_email,
                        password_hash
                    ) VALUES (
                        :identity_id,
                        :user_id,
                        'password',
                        :normalized_email,
                        :normalized_email,
                        :normalized_email,
                        :password_hash
                    )
                    """
                ),
                {
                    "identity_id": identity_id,
                    "user_id": user_id,
                    "normalized_email": "person@example.com",
                    "password_hash": "migration-test-placeholder",
                },
            )

        command.upgrade(alembic_config, "head")

        with engine.connect() as connection:
            normalized_email = connection.execute(
                text("SELECT normalized_email FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            ).scalar_one()

        assert normalized_email == "person@example.com"
    finally:
        engine.dispose()
