"""Database engine, session dependency, and shared SQLAlchemy base."""

from collections.abc import Iterator
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import DateTime, Engine, create_engine, event
from sqlalchemy.engine import Dialect, make_url
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.types import TypeDecorator

from app.config import get_settings
from app.private_fs import create_private_file, make_private_dirs


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware datetimes that stay timezone-aware (UTC) on SQLite, which drops tzinfo."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime; use timezone-aware UTC datetimes")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def create_db_engine(url: str) -> Engine:
    """Create an engine; secure local SQLite paths and enforce foreign keys."""
    parsed = make_url(url)
    is_sqlite = parsed.get_backend_name() == "sqlite"
    db_file = parsed.database

    # Secure ordinary file-backed SQLite databases, but not memory or URI databases.
    is_memory = db_file in (None, "", ":memory:")
    is_uri = bool(parsed.query.get("uri"))

    if is_sqlite and db_file and not is_memory and not is_uri:
        path = Path(db_file)
        make_private_dirs(path.parent)
        create_private_file(path)

    # check_same_thread=False: FastAPI runs sync endpoints in a thread pool.
    engine = create_engine(url, connect_args={"check_same_thread": False} if is_sqlite else {})
    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


@lru_cache
def get_engine() -> Engine:
    return create_db_engine(get_settings().sqlalchemy_url)


def get_session(engine: Annotated[Engine, Depends(get_engine)]) -> Iterator[Session]:
    # expire_on_commit=False: objects stay readable after commit (no hidden reloads).
    with Session(engine, expire_on_commit=False) as session:
        yield session
