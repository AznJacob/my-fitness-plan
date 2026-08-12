from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.database import create_database_session_factory, get_database_session


def build_request(database_session: Session) -> Request:
    app = FastAPI()
    factory = Mock(return_value=database_session)
    app.state.database_session_factory = factory
    return Request({"type": "http", "app": app})


def test_session_factory_binds_sessions_to_engine_without_expiring_on_commit() -> None:
    engine = Mock(spec=Engine)

    factory = create_database_session_factory(engine)

    assert factory.kw["bind"] is engine
    assert factory.kw["expire_on_commit"] is False


def test_database_session_commits_and_closes_after_success() -> None:
    database_session = Mock(spec=Session)
    dependency = get_database_session(build_request(database_session))

    assert next(dependency) is database_session
    with pytest.raises(StopIteration):
        next(dependency)

    database_session.commit.assert_called_once_with()
    database_session.rollback.assert_not_called()
    database_session.close.assert_called_once_with()


def test_database_session_rolls_back_and_closes_after_request_failure() -> None:
    database_session = Mock(spec=Session)
    dependency = get_database_session(build_request(database_session))
    next(dependency)

    with pytest.raises(RuntimeError, match="route failed"):
        dependency.throw(RuntimeError("route failed"))

    database_session.commit.assert_not_called()
    database_session.rollback.assert_called_once_with()
    database_session.close.assert_called_once_with()


def test_database_session_rolls_back_and_closes_after_commit_failure() -> None:
    database_session = Mock(spec=Session)
    database_session.commit.side_effect = SQLAlchemyError("commit failed")
    dependency = get_database_session(build_request(database_session))
    next(dependency)

    with pytest.raises(SQLAlchemyError, match="commit failed"):
        next(dependency)

    database_session.rollback.assert_called_once_with()
    database_session.close.assert_called_once_with()
