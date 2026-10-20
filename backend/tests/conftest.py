from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.config import Settings, get_settings
from app.db import Base, create_db_engine, get_engine
from app.main import app
from tests.helpers import IsolatedSettings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointing at a throwaway data directory, with small limits for fast tests."""
    return IsolatedSettings(
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        max_upload_mb=1,
        max_pages=5,
    )


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    engine = create_db_engine(settings.sqlalchemy_url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def api_client(settings: Settings, engine: Engine) -> Iterator[TestClient]:
    """A client whose app uses the throwaway settings and database above."""
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
