"""Application configuration, loaded from environment variables and an optional .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# <repo>/backend/app/config.py -> <repo>. Resolving the .env path from this file (not the
# current working directory) means the server finds the same file wherever it is started.
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Typed settings. Every field can be overridden with a DOCASSIST_<FIELD> variable."""

    model_config = SettingsConfigDict(
        env_prefix="DOCASSIST_",
        env_file=REPO_ROOT / ".env",
        extra="ignore",
    )

    app_name: str = "Private AI Document Assistant"
    environment: Literal["development", "test", "production"] = "development"
    # Reserved for Stage 2 (document storage). Nothing reads it yet.
    # SQLite is the default; a PostgreSQL URL can be supplied later without code changes.
    database_url: str = "sqlite:///./data/app.db"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings (cached). Used as a FastAPI dependency."""
    return Settings()
