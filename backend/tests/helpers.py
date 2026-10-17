from pathlib import Path

from pydantic_settings import SettingsConfigDict

from app.config import Settings


class IsolatedSettings(Settings):
    """Settings that never read a developer's real .env file (tests must be hermetic)."""

    model_config = SettingsConfigDict(env_file=None)


def settings_from_env_file(env_file: Path) -> Settings:
    """Build Settings that read the given .env file instead of the repository one."""

    class FileSettings(Settings):
        model_config = SettingsConfigDict(env_file=env_file)

    return FileSettings()
