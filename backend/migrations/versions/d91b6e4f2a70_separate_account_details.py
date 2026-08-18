"""Separate account details from per-request planning preferences.

Revision ID: d91b6e4f2a70
Revises: c7e91a4b2d65
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d91b6e4f2a70"
down_revision: str | Sequence[str] | None = "c7e91a4b2d65"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("profiles", "account_details")
    op.drop_constraint("ck_profiles_fitness_goal", "account_details", type_="check")
    op.drop_constraint("ck_profiles_experience_level", "account_details", type_="check")
    op.drop_constraint("ck_profiles_days_per_week", "account_details", type_="check")
    op.drop_constraint("ck_profiles_session_minutes", "account_details", type_="check")
    op.drop_constraint("ck_profiles_equipment_array", "account_details", type_="check")
    op.drop_constraint("ck_profiles_dietary_preferences_array", "account_details", type_="check")
    op.drop_constraint("ck_profiles_wellness_constraints_array", "account_details", type_="check")
    op.alter_column("account_details", "display_name", new_column_name="username")
    op.drop_column("account_details", "fitness_goal")
    op.drop_column("account_details", "experience_level")
    op.drop_column("account_details", "days_per_week")
    op.drop_column("account_details", "session_minutes")
    op.drop_column("account_details", "equipment")
    op.drop_column("account_details", "dietary_preferences")
    op.drop_column("account_details", "wellness_constraints")
    op.add_column("account_details", sa.Column("height_cm", sa.Numeric(5, 1), nullable=True))
    op.add_column("account_details", sa.Column("weight_kg", sa.Numeric(5, 1), nullable=True))
    op.create_check_constraint(
        "ck_account_details_height_cm",
        "account_details",
        "height_cm IS NULL OR height_cm BETWEEN 50 AND 260",
    )
    op.create_check_constraint(
        "ck_account_details_weight_kg",
        "account_details",
        "weight_kg IS NULL OR weight_kg BETWEEN 20 AND 400",
    )


def downgrade() -> None:
    op.drop_constraint("ck_account_details_weight_kg", "account_details", type_="check")
    op.drop_constraint("ck_account_details_height_cm", "account_details", type_="check")
    op.drop_column("account_details", "weight_kg")
    op.drop_column("account_details", "height_cm")
    op.add_column(
        "account_details",
        sa.Column("wellness_constraints", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "account_details",
        sa.Column("dietary_preferences", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "account_details",
        sa.Column("equipment", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "account_details",
        sa.Column("session_minutes", sa.SmallInteger(), nullable=False, server_default="45"),
    )
    op.add_column(
        "account_details",
        sa.Column("days_per_week", sa.SmallInteger(), nullable=False, server_default="3"),
    )
    op.add_column(
        "account_details",
        sa.Column("experience_level", sa.String(20), nullable=False, server_default="beginner"),
    )
    op.add_column(
        "account_details",
        sa.Column("fitness_goal", sa.String(30), nullable=False, server_default="general_fitness"),
    )
    op.alter_column("account_details", "username", new_column_name="display_name")
    op.create_check_constraint(
        "ck_profiles_fitness_goal",
        "account_details",
        "fitness_goal IN ('general_fitness', 'strength', 'muscle_gain', "
        "'endurance', 'weight_management')",
    )
    op.create_check_constraint(
        "ck_profiles_experience_level",
        "account_details",
        "experience_level IN ('beginner', 'intermediate', 'advanced')",
    )
    op.create_check_constraint(
        "ck_profiles_days_per_week", "account_details", "days_per_week BETWEEN 1 AND 7"
    )
    op.create_check_constraint(
        "ck_profiles_session_minutes",
        "account_details",
        "session_minutes BETWEEN 10 AND 180",
    )
    op.create_check_constraint(
        "ck_profiles_equipment_array",
        "account_details",
        "jsonb_typeof(equipment) = 'array'",
    )
    op.create_check_constraint(
        "ck_profiles_dietary_preferences_array",
        "account_details",
        "jsonb_typeof(dietary_preferences) = 'array'",
    )
    op.create_check_constraint(
        "ck_profiles_wellness_constraints_array",
        "account_details",
        "jsonb_typeof(wellness_constraints) = 'array'",
    )
    op.rename_table("account_details", "profiles")
