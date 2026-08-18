import pytest
from pydantic import ValidationError

from app.config import DEFAULT_ANTHROPIC_MODEL, load_settings


def test_settings_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        load_settings()


def test_settings_loads_typed_database_url_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:secret@postgres:5432/myfitnessplan",
    )

    settings = load_settings()

    assert settings.database_url.scheme == "postgresql+psycopg"
    assert settings.database_url.hosts()[0]["host"] == "postgres"
    assert settings.database_url.path == "/myfitnessplan"
    assert "secret" not in repr(settings)


def test_settings_uses_authentication_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:secret@postgres:5432/myfitnessplan",
    )
    monkeypatch.delenv("SESSION_LIFETIME_SECONDS", raising=False)
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("ANTHROPIC_MAX_OUTPUT_TOKENS", raising=False)
    monkeypatch.delenv("ANTHROPIC_MAX_RETRIES", raising=False)
    monkeypatch.delenv("ANTHROPIC_TEMPERATURE", raising=False)

    settings = load_settings()

    assert settings.session_lifetime_seconds == 604_800
    assert settings.session_cookie_secure is False
    assert settings.session_cookie_name == "mfp_session"
    assert settings.csrf_cookie_name == "mfp_csrf"
    assert settings.session_cookie_samesite == "lax"
    assert settings.csrf_header_name == "X-CSRF-Token"
    assert settings.google_client_id is None
    assert settings.anthropic_api_key is None
    assert settings.anthropic_model == DEFAULT_ANTHROPIC_MODEL
    assert settings.anthropic_timeout_seconds == 60
    assert settings.anthropic_max_output_tokens == 6_000
    assert settings.anthropic_max_retries == 0
    assert settings.anthropic_temperature == 0.2


@pytest.mark.parametrize("session_lifetime", ["299", "2678401"])
def test_settings_rejects_session_lifetime_outside_supported_range(
    monkeypatch: pytest.MonkeyPatch,
    session_lifetime: str,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:secret@postgres:5432/myfitnessplan",
    )
    monkeypatch.setenv("SESSION_LIFETIME_SECONDS", session_lifetime)

    with pytest.raises(ValidationError, match="session_lifetime_seconds"):
        load_settings()


def test_settings_rejects_database_url_for_a_different_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://app_user:secret@postgres:5432/myfitnessplan",
    )

    with pytest.raises(
        ValidationError,
        match=r"DATABASE_URL must use the postgresql\+psycopg scheme",
    ):
        load_settings()


def test_settings_loads_bounded_anthropic_configuration_without_exposing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:secret@postgres:5432/myfitnessplan",
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", " custom-haiku-snapshot ")
    monkeypatch.setenv("ANTHROPIC_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("ANTHROPIC_MAX_OUTPUT_TOKENS", "4096")
    monkeypatch.setenv("ANTHROPIC_MAX_RETRIES", "1")
    monkeypatch.setenv("ANTHROPIC_TEMPERATURE", "0.1")

    settings = load_settings()

    assert settings.anthropic_api_key is not None
    assert settings.anthropic_api_key.get_secret_value() == "test-anthropic-key"
    assert "test-anthropic-key" not in repr(settings)
    assert settings.anthropic_model == "custom-haiku-snapshot"
    assert settings.anthropic_timeout_seconds == 45
    assert settings.anthropic_max_output_tokens == 4_096
    assert settings.anthropic_max_retries == 1
    assert settings.anthropic_temperature == 0.1


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("ANTHROPIC_TIMEOUT_SECONDS", "4"),
        ("ANTHROPIC_TIMEOUT_SECONDS", "301"),
        ("ANTHROPIC_MAX_OUTPUT_TOKENS", "511"),
        ("ANTHROPIC_MAX_OUTPUT_TOKENS", "10001"),
        ("ANTHROPIC_MAX_RETRIES", "2"),
        ("ANTHROPIC_TEMPERATURE", "1.1"),
        ("ANTHROPIC_MODEL", "   "),
    ],
)
def test_settings_rejects_unbounded_anthropic_configuration(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:secret@postgres:5432/myfitnessplan",
    )
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        load_settings()
