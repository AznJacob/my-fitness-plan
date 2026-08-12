from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class whose metadata Alembic will consume in stage 4."""


class TimestampMixin:
    """Common creation and modification timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(TimestampMixin, Base):
    """Application-owned identity shared by all sign-in methods."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "normalized_email = lower(normalized_email)",
            name="ck_users_normalized_email",
        ),
        UniqueConstraint("normalized_email", name="uq_users_normalized_email"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    normalized_email: Mapped[str] = mapped_column(String(320), nullable=False)

    authentication_identities: Mapped[list[AuthenticationIdentity]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    profile: Mapped[Profile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    plans: Mapped[list[Plan]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AuthenticationIdentity(TimestampMixin, Base):
    """A password or Google identity linked to an application user."""

    __tablename__ = "authentication_identities"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('password', 'google')",
            name="ck_authentication_identities_provider",
        ),
        CheckConstraint(
            "normalized_email = lower(normalized_email)",
            name="ck_authentication_identities_normalized_email",
        ),
        CheckConstraint(
            "(provider = 'password' AND password_hash IS NOT NULL) OR "
            "(provider = 'google' AND password_hash IS NULL)",
            name="ck_authentication_identities_password_hash",
        ),
        UniqueConstraint(
            "provider",
            "provider_subject",
            name="uq_authentication_identities_provider_subject",
        ),
        UniqueConstraint(
            "user_id",
            "provider",
            name="uq_authentication_identities_user_provider",
        ),
        Index(
            "uq_authentication_identities_password_email",
            "normalized_email",
            unique=True,
            postgresql_where=text("provider = 'password'"),
        ),
        Index("ix_authentication_identities_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    password_hash: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="authentication_identities")


class UserSession(TimestampMixin, Base):
    """A revocable application session whose raw tokens exist only in cookies."""

    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("octet_length(token_hash) = 32", name="ck_sessions_token_hash_length"),
        CheckConstraint(
            "octet_length(csrf_token_hash) = 32",
            name="ck_sessions_csrf_token_hash_length",
        ),
        CheckConstraint("expires_at > created_at", name="ck_sessions_expiration"),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_sessions_revocation",
        ),
        Index("uq_sessions_token_hash", "token_hash", unique=True),
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    csrf_token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class Profile(TimestampMixin, Base):
    """A user's current general-wellness planning preferences."""

    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint(
            "fitness_goal IN "
            "('general_fitness', 'strength', 'muscle_gain', 'endurance', 'weight_management')",
            name="ck_profiles_fitness_goal",
        ),
        CheckConstraint(
            "experience_level IN ('beginner', 'intermediate', 'advanced')",
            name="ck_profiles_experience_level",
        ),
        CheckConstraint(
            "days_per_week BETWEEN 1 AND 7",
            name="ck_profiles_days_per_week",
        ),
        CheckConstraint(
            "session_minutes BETWEEN 1 AND 1440",
            name="ck_profiles_session_minutes",
        ),
        CheckConstraint("jsonb_typeof(equipment) = 'array'", name="ck_profiles_equipment_array"),
        CheckConstraint(
            "jsonb_typeof(dietary_preferences) = 'array'",
            name="ck_profiles_dietary_preferences_array",
        ),
        CheckConstraint(
            "jsonb_typeof(wellness_constraints) = 'array'",
            name="ck_profiles_wellness_constraints_array",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(100))
    fitness_goal: Mapped[str] = mapped_column(String(30), nullable=False)
    experience_level: Mapped[str] = mapped_column(String(20), nullable=False)
    days_per_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    session_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    equipment: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    dietary_preferences: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    wellness_constraints: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    user: Mapped[User] = relationship(back_populates="profile")


class Plan(TimestampMixin, Base):
    """A persisted, validated workout and nutrition plan."""

    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('inactive', 'active', 'archived')",
            name="ck_plans_status",
        ),
        CheckConstraint("schema_version > 0", name="ck_plans_schema_version"),
        CheckConstraint(
            "jsonb_typeof(profile_snapshot) = 'object'",
            name="ck_plans_profile_snapshot_object",
        ),
        CheckConstraint(
            "jsonb_typeof(workout_plan) = 'object'",
            name="ck_plans_workout_plan_object",
        ),
        CheckConstraint(
            "jsonb_typeof(nutrition_plan) = 'object'",
            name="ck_plans_nutrition_plan_object",
        ),
        CheckConstraint(
            "(status = 'archived' AND archived_at IS NOT NULL) OR "
            "(status <> 'archived' AND archived_at IS NULL)",
            name="ck_plans_archived_at",
        ),
        Index(
            "uq_plans_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_plans_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'inactive'"),
    )
    schema_version: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default=text("1"),
    )
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    workout_plan: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    nutrition_plan: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="plans")
