"""DB engine and per-request session for the persistence service.

Mirrors colombus's engine configuration: ``pool_pre_ping`` to guard against
stale pooled connections, and a per-connection ``statement_timeout`` derived
from the ``QUERY_TIMEOUT_SECONDS`` setting so runaway queries are aborted.
The engine URL comes from :attr:`app.core.config.settings.DATABASE_URL`.
"""

from collections.abc import Generator

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.core.config import settings


def create_db_engine(database_url: str | None = None) -> Engine:
    """Build the SQLAlchemy engine for the given URL (defaults to settings)."""
    url = database_url or str(settings.DATABASE_URL)
    return create_engine(
        url,
        echo=False,
        pool_pre_ping=True,
        connect_args={
            "options": f"-c statement_timeout={settings.QUERY_TIMEOUT_SECONDS * 1000}"
        },
    )


engine: Engine = create_db_engine()


def get_session() -> Generator[Session]:
    """Yield a transactional DB session bound to the application engine."""
    with Session(engine) as session:
        yield session


DatabaseSession = Generator[Session]
