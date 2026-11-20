import json
from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

import app.db.models  # noqa: F401  (register tables on SQLModel.metadata)
from app.main import app  # noqa: E402
from tests.profile_types import ProfileJson

FIXTURES_DIR = Path(__file__).parent / "fixtures"

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
