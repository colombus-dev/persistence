from sqlalchemy import Engine
from sqlmodel import Session, create_engine

from app.core.config import settings

engine: Engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


def init_db(session: Session) -> None:
    # tables are created with Alembic migrations
    # insert initial data in the database
    ...
