"""Application configuration, loaded from environment variables and an optional .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
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
    # Upload limits. Processing happens inside the upload request, so keep these modest.
    max_upload_mb: int = Field(default=20, ge=1, le=200)
    max_pages: int = Field(default=200, ge=1, le=5000)

    # Where uploaded PDFs and the default SQLite database live (gitignored).
    data_dir: Path = REPO_ROOT / "data"
    # Optional override, e.g. a PostgreSQL URL. Defaults to SQLite inside data_dir.
    database_url: str | None = None

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def sqlalchemy_url(self) -> str:
        return self.database_url or f"sqlite:///{self.data_dir / 'app.db'}"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings (cached). Used as a FastAPI dependency."""
    return Settings()
