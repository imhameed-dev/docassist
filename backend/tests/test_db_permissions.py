"""Permissions for local SQLite databases."""

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

from app.db import create_db_engine


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
@pytest.mark.parametrize("umask", [0, 0o022, 0o277])
def test_new_database_and_directories_are_private(tmp_path: Path, umask: int) -> None:
    db_path = tmp_path / "private" / "nested" / "app.db"
    previous_umask = os.umask(umask)
    try:
        engine = create_db_engine(f"sqlite:///{db_path}")
    finally:
        os.umask(previous_umask)

    try:
        assert os.stat(db_path.parent).st_mode & 0o777 == 0o700
        assert os.stat(db_path.parent.parent).st_mode & 0o777 == 0o700
        assert os.stat(db_path).st_mode & 0o777 == 0o600
    finally:
        engine.dispose()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_existing_database_permissions_are_not_changed(tmp_path: Path) -> None:
    db_path = tmp_path / "existing.db"
    db_path.touch()
    db_path.chmod(0o644)

    engine = create_db_engine(f"sqlite:///{db_path}")
    try:
        assert os.stat(db_path).st_mode & 0o777 == 0o644
    finally:
        engine.dispose()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission bits")
def test_existing_parent_directory_permissions_are_not_changed(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "existing"
    parent.mkdir()
    parent.chmod(0o755)
    db_path = parent / "app.db"

    engine = create_db_engine(f"sqlite:///{db_path}")
    try:
        assert os.stat(parent).st_mode & 0o777 == 0o755
        assert os.stat(db_path).st_mode & 0o777 == 0o600
    finally:
        engine.dispose()


def test_sqlite_foreign_keys_remain_enabled(tmp_path: Path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'foreign-keys.db'}")
    try:
        with engine.connect() as connection:
            enabled = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
        assert enabled == 1
    finally:
        engine.dispose()
