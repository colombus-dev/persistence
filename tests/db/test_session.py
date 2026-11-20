"""Tests for the DB engine + session dependency (slice 3).

These pin the engine configuration (pool_pre_ping, statement_timeout derived
from the query-timeout setting) and that ``get_session`` yields a live session
that can run queries against the database. Mirrors colombus's engine/session
behaviour so the migration target is faithful.
"""

from typing import Any

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import text

import app.db.session as db_session
from tests.conftest import TEST_DATABASE_URL


def test_query_timeout_setting_defaults_to_colombus_value() -> None:
    """The query-timeout setting defaults to colombus's 10 seconds."""
    from app.core.config import settings

    assert settings.QUERY_TIMEOUT_SECONDS == 10


@pytest.mark.parametrize(
    "engine_kwargs",
    [
        {"pool_pre_ping": True},
        {
            "connect_args": {
                "options": "-c statement_timeout=10000",
            }
        },
    ],
)
def test_engine_config_carries_pre_ping_and_statement_timeout(
    monkeypatch: pytest.MonkeyPatch, engine_kwargs: dict[str, Any]
) -> None:
    """The engine must use pool_pre_ping and a statement_timeout connect arg
    derived from QUERY_TIMEOUT_SECONDS, matching colombus."""

    captured: list[dict[str, Any]] = []
    real_create_engine = db_session.create_engine

    def recorder(url: str, **kwargs: Any) -> Engine:
        captured.append(kwargs)
        return real_create_engine(url, **kwargs)

    monkeypatch.setattr(db_session, "create_engine", recorder)
    db_session.create_db_engine(TEST_DATABASE_URL)

    assert len(captured) == 1
    for key, value in engine_kwargs.items():
        assert captured[0][key] == value


def test_get_session_yields_live_session(
    monkeypatch: pytest.MonkeyPatch, engine: Engine
) -> None:
    """get_session must yield a session bound to the engine that can query."""
    monkeypatch.setattr(db_session, "engine", engine)

    gen = db_session.get_session()
    session = next(gen)
    try:
        row = session.exec(text("SELECT 1 AS one")).one()
        assert row.one == 1
        assert session.bind is engine  # type: ignore[union-attr]
    finally:
        gen.close()
