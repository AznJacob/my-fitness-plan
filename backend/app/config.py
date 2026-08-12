from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SessionLifetimeSeconds = Annotated[int, Field(ge=300, le=2_678_400)]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    database_url: PostgresDsn = Field(repr=False)
    cors_allowed_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [
            AnyHttpUrl("http://localhost:5173"),
            AnyHttpUrl("http://127.0.0.1:5173"),
        ]
    )
    session_lifetime_seconds: SessionLifetimeSeconds = 60 * 60 * 24 * 7
    session_cookie_secure: bool = False
    google_client_id: str | None = Field(default=None, repr=False)

    @field_validator("database_url")
    @classmethod
    def require_psycopg_driver(cls, value: PostgresDsn) -> PostgresDsn:
        if value.scheme != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use the postgresql+psycopg scheme")
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def require_origins_without_paths(
        cls,
        origins: list[AnyHttpUrl],
    ) -> list[AnyHttpUrl]:
        if not origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one origin")

        for origin in origins:
            has_non_origin_component = (
                origin.username is not None
                or origin.password is not None
                or origin.path not in (None, "/")
                or origin.query is not None
                or origin.fragment is not None
            )
            if has_non_origin_component:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS entries must be origins without credentials, paths, "
                    "queries, or fragments"
                )
        return origins

    @field_validator("google_client_id", mode="before")
    @classmethod
    def treat_empty_google_client_id_as_unconfigured(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @property
    def session_cookie_name(self) -> str:
        """Return the fixed host-only session-cookie name."""
        return "mfp_session"

    @property
    def csrf_cookie_name(self) -> str:
        """Return the fixed JavaScript-readable CSRF-cookie name."""
        return "mfp_csrf"

    @property
    def session_cookie_samesite(self) -> Literal["lax"]:
        """Keep the selected SameSite policy typed for response-cookie calls."""
        return "lax"

    @property
    def csrf_header_name(self) -> str:
        """Return the single custom header accepted for CSRF validation."""
        return "X-CSRF-Token"

    @property
    def cors_allowed_origin_strings(self) -> list[str]:
        """Return normalized origins in the form expected by CORS middleware."""
        return [str(origin).removesuffix("/") for origin in self.cors_allowed_origins]


def load_settings() -> Settings:
    """Load and validate settings from the process environment."""
    return Settings()  # type: ignore[call-arg]
