"""Private filesystem helpers for local application data."""

import os
from pathlib import Path

PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


def make_private_dirs(path: Path) -> None:
    """Create missing directories with owner-only permissions.

    Existing directories are left unchanged.
    """
    missing: list[Path] = []
    current = path

    while not current.exists():
        missing.append(current)
        parent = current.parent
        if parent == current:
            raise OSError(f"could not find an existing parent for {path}")
        current = parent

    for directory in reversed(missing):
        try:
            directory.mkdir(mode=PRIVATE_DIR_MODE)
        except FileExistsError:
            # Another process may have created it concurrently.
            continue
        directory.chmod(PRIVATE_DIR_MODE)


def create_private_file(path: Path) -> bool:
    """Create an empty owner-only file; return False if it already exists."""
    try:
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            PRIVATE_FILE_MODE,
        )
    except FileExistsError:
        return False

    try:
        if os.name != "nt":
            os.fchmod(fd, PRIVATE_FILE_MODE)
    finally:
        os.close(fd)

    return True
