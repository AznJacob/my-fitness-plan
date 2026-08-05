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
