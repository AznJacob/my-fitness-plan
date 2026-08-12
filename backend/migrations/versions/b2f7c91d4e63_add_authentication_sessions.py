"""add authentication sessions

Revision ID: b2f7c91d4e63
Revises: 7768cfd3a397
Create Date: 2026-08-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2f7c91d4e63"
down_revision: str | Sequence[str] | None = "7768cfd3a397"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add canonical user emails and revocable database-backed sessions."""
    op.add_column(
        "users",
        sa.Column("normalized_email", sa.String(length=320), nullable=True),
    )

    # Milestones 1-4 had no user-creation API, but preserve any valid manually seeded data.
    # A user with no single identity email is ambiguous and must be repaired before retrying.
    op.execute(
        """
        UPDATE users AS application_user
        SET normalized_email = identity_email.normalized_email
        FROM (
            SELECT user_id, min(normalized_email) AS normalized_email
            FROM authentication_identities
            GROUP BY user_id
            HAVING count(DISTINCT normalized_email) = 1
        ) AS identity_email
        WHERE application_user.id = identity_email.user_id
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM users WHERE normalized_email IS NULL) THEN
                RAISE EXCEPTION
                    'Cannot add canonical email: every existing user must have one identity email';
            END IF;
        END
        $$
        """
    )

    op.alter_column("users", "normalized_email", existing_type=sa.String(320), nullable=False)
    op.create_check_constraint(
        "ck_users_normalized_email",
        "users",
        "normalized_email = lower(normalized_email)",
    )
    op.create_unique_constraint("uq_users_normalized_email", "users", ["normalized_email"])

    op.create_table(
        "sessions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("csrf_token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "octet_length(token_hash) = 32",
            name="ck_sessions_token_hash_length",
        ),
        sa.CheckConstraint(
            "octet_length(csrf_token_hash) = 32",
            name="ck_sessions_csrf_token_hash_length",
        ),
        sa.CheckConstraint("expires_at > created_at", name="ck_sessions_expiration"),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_sessions_revocation",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"], unique=False)
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_index("uq_sessions_token_hash", "sessions", ["token_hash"], unique=True)


def downgrade() -> None:
    """Remove sessions and the canonical user email."""
    op.drop_index("uq_sessions_token_hash", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_table("sessions")
    op.drop_constraint("uq_users_normalized_email", "users", type_="unique")
    op.drop_constraint("ck_users_normalized_email", "users", type_="check")
    op.drop_column("users", "normalized_email")
