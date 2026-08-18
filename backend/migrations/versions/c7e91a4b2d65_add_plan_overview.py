"""add plan overview

Revision ID: c7e91a4b2d65
Revises: 8d4f6a2c1b90
Create Date: 2026-08-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7e91a4b2d65"
down_revision: str | Sequence[str] | None = "8d4f6a2c1b90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_OVERVIEW = "Generated general-wellness plan."


def upgrade() -> None:
    """Store the validated plan overview that was absent from the initial schema."""
    op.add_column(
        "plans",
        sa.Column(
            "overview",
            sa.String(length=500),
            nullable=False,
            server_default=_LEGACY_OVERVIEW,
        ),
    )
    op.alter_column("plans", "overview", server_default=None)


def downgrade() -> None:
    """Remove the plan overview column."""
    op.drop_column("plans", "overview")
