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
from sqlalchemy.engine import Engine, Inspector
from sqlalchemy.sql.schema import Table
from sqlmodel import SQLModel, Session, create_engine, inspect, select

from app.db.models import Profile, Project
from tests.profile_types import ProfileJson
from tests.profile_utils import encode_profile, ingest_profile

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


def _db_columns(inspector: "Inspector", table: str) -> dict[str, bool]:
    """Map migrated column name -> nullable from the inspector."""
    return {col["name"]: bool(col["nullable"]) for col in inspector.get_columns(table)}


def _db_pk(inspector: "Inspector", table: str) -> set[str]:
    """Primary-key column names of a migrated table."""
    return set(inspector.get_pk_constraint(table)["constrained_columns"])


def _model_columns(table: "Table") -> dict[str, bool]:
    """Map model column name -> nullable from the metadata."""
    return {col.name: bool(col.nullable) for col in table.columns}


def _model_pk(table: "Table") -> set[str]:
    """Primary-key column names from the model metadata."""
    return {col.name for col in table.primary_key.columns}


def test_baseline_migration_column_parity() -> None:
    """Every migrated column matches the models on name, nullability and PK.

    Complements the table-name check: a migration that renames, drops, makes
    nullable, or changes the primary key of any column now fails the suite
    instead of silently diverging. Column SQL types are not compared here
    because SQLModel's ``AutoString``/``Uuid`` render as Postgres
    ``VARCHAR``/``UUID`` in the inspector; the round-trip test covers value
    fidelity.
    """
    config = _alembic_config()
    _reset_to_head(config)

    engine: Engine = create_engine(MIGRATION_DB_URL)
    try:
        inspector = inspect(engine)
        for table_name, table in SQLModel.metadata.tables.items():
            db_cols = _db_columns(inspector, table_name)
            model_cols = _model_columns(table)
            assert set(db_cols) == set(model_cols), (
                f"column set differs for {table_name!r}: "
                f"DB={sorted(db_cols)} model={sorted(model_cols)}"
            )
            for name in model_cols:
                assert db_cols[name] == model_cols[name], (
                    f"column {table_name}.{name} nullable: DB={db_cols[name]} "
                    f"model={model_cols[name]}"
                )
            db_pk = _db_pk(inspector, table_name)
            model_pk = _model_pk(table)
            assert db_pk == model_pk, (
                f"primary key differs for {table_name!r}: DB={sorted(db_pk)} "
                f"model={sorted(model_pk)}"
            )
    finally:
        engine.dispose()


def test_baseline_profile_roundtrips_through_migrated_db(
    full_profile: ProfileJson,
) -> None:
    """A profile written to the migrated schema reloads identically.

    Complements the column-parity test: it can't type-check because SQLModel's
    ``AutoString``/``Uuid`` render as Postgres ``VARCHAR``/``UUID`` in the
    inspector, so a round-trip against the migrated DB is the real guard that
    the migrated columns store and reload values correctly.
    """
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
            assert profile.encoded_profile == encode_profile(full_profile)
    finally:
        engine.dispose()
