from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from app import main


def test_health_endpoint_returns_ok_status_after_database_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:secret@postgres:5432/myfitnessplan",
    )
    engine = Mock(spec=Engine)
    session_factory = Mock()
    create_engine = Mock(return_value=engine)
    create_session_factory = Mock(return_value=session_factory)
    verify_connection = Mock()
    monkeypatch.setattr(main, "create_database_engine", create_engine)
    monkeypatch.setattr(main, "create_database_session_factory", create_session_factory)
    monkeypatch.setattr(main, "verify_database_connection", verify_connection)

    with TestClient(main.app) as client:
        assert main.app.state.database_session_factory is session_factory
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "my-fitness-plan-backend"}
    create_engine.assert_called_once()
    verify_connection.assert_called_once_with(engine)
    create_session_factory.assert_called_once_with(engine)
    engine.dispose.assert_called_once_with()


def test_application_startup_fails_when_database_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:secret@postgres:5432/myfitnessplan",
    )
    engine = Mock(spec=Engine)
    monkeypatch.setattr(main, "create_database_engine", Mock(return_value=engine))
    monkeypatch.setattr(
        main,
        "verify_database_connection",
        Mock(side_effect=SQLAlchemyError("database unavailable")),
    )

    with pytest.raises(SQLAlchemyError, match="database unavailable"):
        with TestClient(main.app):
            pass

    engine.dispose.assert_called_once_with()
