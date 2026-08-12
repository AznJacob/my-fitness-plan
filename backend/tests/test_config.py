import pytest
from pydantic import ValidationError

from app.config import load_settings


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
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("SESSION_LIFETIME_SECONDS", raising=False)
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

    settings = load_settings()

    assert settings.cors_allowed_origin_strings == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    assert settings.session_lifetime_seconds == 604_800
    assert settings.session_cookie_secure is False
    assert settings.session_cookie_name == "mfp_session"
    assert settings.csrf_cookie_name == "mfp_csrf"
    assert settings.session_cookie_samesite == "lax"
    assert settings.csrf_header_name == "X-CSRF-Token"
    assert settings.google_client_id is None


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


def test_settings_rejects_cors_origin_with_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:secret@postgres:5432/myfitnessplan",
    )
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", '["http://localhost:5173/api"]')

    with pytest.raises(ValidationError, match="must be origins without credentials"):
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
