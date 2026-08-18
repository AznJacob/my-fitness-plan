"""limit profile session minutes

Revision ID: 8d4f6a2c1b90
Revises: b2f7c91d4e63
Create Date: 2026-08-17 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "8d4f6a2c1b90"
down_revision: str | Sequence[str] | None = "b2f7c91d4e63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the general-wellness MVP session-duration boundary."""
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM profiles WHERE session_minutes NOT BETWEEN 10 AND 180
            ) THEN
                RAISE EXCEPTION
                    'Cannot limit session minutes: update profile values to the 10-180 range';
            END IF;
        END
        $$
        """
    )
    op.drop_constraint("ck_profiles_session_minutes", "profiles", type_="check")
    op.create_check_constraint(
        "ck_profiles_session_minutes",
        "profiles",
        "session_minutes BETWEEN 10 AND 180",
    )


def downgrade() -> None:
    """Restore the original broad storage boundary."""
    op.drop_constraint("ck_profiles_session_minutes", "profiles", type_="check")
    op.create_check_constraint(
        "ck_profiles_session_minutes",
        "profiles",
        "session_minutes BETWEEN 1 AND 1440",
    )
