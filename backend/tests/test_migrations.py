from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.db import Base, create_db_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def test_migrations_produce_the_schema_the_models_expect(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    command.upgrade(alembic_config(url), "head")
    engine = create_db_engine(url)
    try:
        with engine.connect() as connection:
            # compare_type is off: the models use a custom timezone-aware datetime type whose
            # column type would otherwise be reported as a (harmless) difference.
            context = MigrationContext.configure(connection, opts={"compare_type": False})
            assert compare_metadata(context, Base.metadata) == []
    finally:
        engine.dispose()


def test_migrations_can_be_reversed(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'reversed.db'}"
    config = alembic_config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    engine = create_db_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert "documents" not in tables
    assert "pages" not in tables
