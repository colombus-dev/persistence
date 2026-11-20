"""Verify the Alembic migration reproduces the domain schema.

Runs ``alembic upgrade head`` against a dedicated, empty database and checks
that the resulting tables match ``app.db.models.SQLModel.metadata``. This guards
against the schema drifting from the models (a missing/wrong migration fails the
suite instead of silently diverging).

The migration runs against the dedicated ``app_mig_test`` database via the
``ALEMBIC_DATABASE_URL`` override, so the shared ``app_test`` engine fixture is
never touched.
"""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, Session, create_engine, inspect, select

from app.db.models import Profile, Project
from tests.profile_types import ProfileJson
from tests.profile_utils import ingest_profile

MIGRATION_DB_URL = (
    "postgresql+psycopg://postgres:colombus_persistence_password"
    "@localhost:5432/app_mig_test"
)

ALEMBIC_INI = Path("alembic.ini")


def _alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", "app/alembic")
    return config


def _upgrade(config: Config) -> None:
    os.environ["ALEMBIC_DATABASE_URL"] = MIGRATION_DB_URL
    try:
        command.upgrade(config, "head")
    finally:
        os.environ.pop("ALEMBIC_DATABASE_URL", None)


def _reset_to_head(config: Config) -> None:
    os.environ["ALEMBIC_DATABASE_URL"] = MIGRATION_DB_URL
    try:
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        os.environ.pop("ALEMBIC_DATABASE_URL", None)


def test_baseline_migration_builds_all_domain_tables() -> None:
    """Upgrading to head creates exactly the model's tables (mod alembic_version)."""
    config = _alembic_config()
    _reset_to_head(config)

    engine: Engine = create_engine(MIGRATION_DB_URL)
    try:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
    finally:
        engine.dispose()

    model_tables = set(SQLModel.metadata.tables)
    assert table_names - {"alembic_version"} == model_tables
    assert not table_names.isdisjoint(model_tables)


def test_baseline_profile_roundtrips_through_migrated_db(
    full_profile: ProfileJson,
) -> None:
    """A profile written to the migrated schema reloads identically."""
    config = _alembic_config()
    _upgrade(config)

    engine: Engine = create_engine(MIGRATION_DB_URL)
    try:
        with Session(engine) as session:
            project = Project(name="mig-proj")
            session.add(project)
            session.flush()
            ingest_profile(session, project.id, full_profile)
            session.commit()

            profile = session.exec(
                select(Profile).where(Profile.name == full_profile["name"])
            ).one()
            assert profile.name == full_profile["name"]
            assert profile.json_profile == full_profile
    finally:
        engine.dispose()
