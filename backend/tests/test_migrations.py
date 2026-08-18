from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_HEAD = "d91b6e4f2a70"


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
            "account_details",
            "authentication_identities",
            "plans",
            "sessions",
            "users",
        }

        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == (MIGRATION_HEAD)

        for table_name in ("authentication_identities", "account_details", "plans", "sessions"):
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
        plan_columns = {column["name"]: column for column in inspector.get_columns("plans")}
        assert plan_columns["overview"]["nullable"] is False

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

        account_checks = {
            constraint["name"]: constraint["sqltext"]
            for constraint in inspector.get_check_constraints("account_details")
        }
        assert "50" in account_checks["ck_account_details_height_cm"]
        assert "400" in account_checks["ck_account_details_weight_kg"]
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


@pytest.mark.integration
def test_plan_overview_migration_backfills_existing_plans(
    empty_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", empty_database_url)
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    engine = create_engine(empty_database_url)
    user_id = uuid4()
    plan_id = uuid4()

    try:
        command.upgrade(alembic_config, "8d4f6a2c1b90")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, normalized_email) "
                    "VALUES (:user_id, 'migration@example.com')"
                ),
                {"user_id": user_id},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO plans (
                        id, user_id, title, profile_snapshot, workout_plan, nutrition_plan
                    ) VALUES (
                        :plan_id, :user_id, 'Legacy plan', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb
                    )
                    """
                ),
                {"plan_id": plan_id, "user_id": user_id},
            )

        command.upgrade(alembic_config, "head")

        with engine.connect() as connection:
            overview = connection.execute(
                text("SELECT overview FROM plans WHERE id = :plan_id"),
                {"plan_id": plan_id},
            ).scalar_one()

        assert overview == "Generated general-wellness plan."
        plan_columns = {column["name"]: column for column in inspect(engine).get_columns("plans")}
        assert plan_columns["overview"]["nullable"] is False
    finally:
        engine.dispose()
