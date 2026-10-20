"""Alembic environment: uses the application's settings and models."""

from alembic import context

import app.models  # noqa: F401  (importing registers the tables on Base.metadata)
from app.config import get_settings
from app.db import Base, create_db_engine

config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    # An explicit URL (used by tests) wins; otherwise use the application's settings.
    return config.get_main_option("sqlalchemy.url") or get_settings().sqlalchemy_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_db_engine(_database_url())
    try:
        with engine.connect() as connection:
            # render_as_batch: lets later migrations alter SQLite tables.
            context.configure(
                connection=connection, target_metadata=target_metadata, render_as_batch=True
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
