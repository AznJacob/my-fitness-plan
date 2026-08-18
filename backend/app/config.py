from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SessionLifetimeSeconds = Annotated[int, Field(ge=300, le=2_678_400)]
AnthropicTimeoutSeconds = Annotated[float, Field(ge=5, le=300)]
AnthropicMaxOutputTokens = Annotated[int, Field(ge=512, le=10_000)]
AnthropicMaxRetries = Annotated[int, Field(ge=0, le=1)]
AnthropicTemperature = Annotated[float, Field(ge=0, le=1)]
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
LOCAL_FRONTEND_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    database_url: PostgresDsn = Field(repr=False)
    session_lifetime_seconds: SessionLifetimeSeconds = 60 * 60 * 24 * 7
    session_cookie_secure: bool = False
    google_client_id: str | None = Field(default=None, repr=False)
    anthropic_api_key: SecretStr | None = Field(default=None, repr=False)
    anthropic_model: str = DEFAULT_ANTHROPIC_MODEL
    anthropic_timeout_seconds: AnthropicTimeoutSeconds = 60
    anthropic_max_output_tokens: AnthropicMaxOutputTokens = 6_000
    anthropic_max_retries: AnthropicMaxRetries = 0
    anthropic_temperature: AnthropicTemperature = 0.2

    @field_validator("database_url")
    @classmethod
    def require_psycopg_driver(cls, value: PostgresDsn) -> PostgresDsn:
        if value.scheme != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use the postgresql+psycopg scheme")
        return value

    @field_validator("google_client_id", "anthropic_api_key", mode="before")
    @classmethod
    def treat_empty_optional_secret_as_unconfigured(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("anthropic_model")
    @classmethod
    def require_nonempty_anthropic_model(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("ANTHROPIC_MODEL must not be empty")
        return normalized_value

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


def load_settings() -> Settings:
    """Load and validate settings from the process environment."""
    return Settings()  # type: ignore[call-arg]
