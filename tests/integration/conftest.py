import json
import re
from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

import app.db.models  # noqa: F401  (register tables on SQLModel.metadata)
from app.main import app  # noqa: E402
from tests.profile_types import ProfileJson

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Dedicated test database on localhost (not the docker-network prod URL).
TEST_DATABASE_URL = (
    "postgresql+psycopg://postgres:colombus_persistence_password"
    "@localhost:5432/app_test"
)


@pytest.fixture(scope="session")
def engine() -> Generator[Engine]:
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session(engine: Engine) -> Generator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    sess = Session(bind=connection, expire_on_commit=False)
    try:
        yield sess
    finally:
        sess.close()
        transaction.rollback()
        connection.close()


class _QueryCounter:
    """Count live SQL statements issued against an engine during a block.

    A plain event-listener counter (no DB state). ``count`` filters statements
    bound to a ``FROM <table>`` read so tests can assert bounded queries (N+1
    guards) without asserting on incidental statements.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._statements: list[str] = []
        event.listen(engine, "before_cursor_execute", self._record)

    def close(self) -> None:
        event.remove(self._engine, "before_cursor_execute", self._record)

    def reset(self) -> None:
        self._statements.clear()

    def _record(self, _conn, _cursor, statement, _params, _ctx, _executemany) -> None:
        self._statements.append(statement)

    def count(self, table: str) -> int:
        pattern = re.compile(rf"\bfrom\s+{re.escape(table)}\b", re.IGNORECASE)
        return sum(1 for s in self._statements if pattern.search(s))


@pytest.fixture()
def assert_queries(session: Session) -> Generator[_QueryCounter]:
    """Tally SQL statements on the test engine via ``before_cursor_execute``.

    Feed the query you want to measure, then assert on ``counter.count("<table>")``::

        data = _execute(session, "{ matchingProfiles { profile { name } } }")
        assert assert_queries.count("profile") == 1

    The counter records every statement seen so far; re-run the query (after
    ``session.expunge_all()`` to drop identity-map hits) and assert the count
    stays bounded.
    """
    counter = _QueryCounter(session.get_bind())
    try:
        yield counter
    finally:
        counter.close()


@pytest.fixture(scope="session")
def mini_profile() -> ProfileJson:
    path = FIXTURES_DIR / "profiles" / "mini_profile.json"
    return cast(ProfileJson, json.loads(path.read_text()))


@pytest.fixture(scope="session")
def full_profile() -> ProfileJson:
    path = FIXTURES_DIR / "profiles" / "student_0.json"
    return cast(ProfileJson, json.loads(path.read_text()))


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c
