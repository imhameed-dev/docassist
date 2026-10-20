import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from tests.helpers import IsolatedSettings, settings_from_env_file

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make tests independent of any DOCASSIST_* variables in the developer's shell."""
    for key in list(os.environ):
        if key.startswith("DOCASSIST_"):
            monkeypatch.delenv(key)


def test_defaults() -> None:
    settings = IsolatedSettings()
    assert settings.environment == "development"
    assert settings.database_url is None
    assert settings.sqlalchemy_url.startswith("sqlite:///")
    assert settings.sqlalchemy_url.endswith("app.db")
    assert settings.max_upload_mb == 20
    assert settings.uploads_dir == settings.data_dir / "uploads"


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCASSIST_ENVIRONMENT", "production")
    monkeypatch.setenv("DOCASSIST_DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    settings = IsolatedSettings()
    assert settings.environment == "production"
    assert settings.sqlalchemy_url == "postgresql+psycopg://u:p@localhost/db"


def test_env_file_is_read(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DOCASSIST_APP_NAME=From File\n")
    assert settings_from_env_file(env_file).app_name == "From File"


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCASSIST_ENVIRONMENT", "staging")
    with pytest.raises(ValidationError):
        IsolatedSettings()


def test_upload_limits_must_be_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCASSIST_MAX_UPLOAD_MB", "0")
    with pytest.raises(ValidationError):
        IsolatedSettings()


def test_max_upload_bytes() -> None:
    assert IsolatedSettings(max_upload_mb=2).max_upload_bytes == 2 * 1024 * 1024


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
    get_settings.cache_clear()


def test_env_example_only_contains_known_settings() -> None:
    """Guards against .env.example drifting away from the real Settings fields."""
    prefix = "DOCASSIST_"
    keys = [
        line.split("=", 1)[0].strip()
        for line in (REPO_ROOT / ".env.example").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert keys, ".env.example should define at least one variable"
    for key in keys:
        assert key.startswith(prefix), key
        assert key.removeprefix(prefix).lower() in Settings.model_fields, key
