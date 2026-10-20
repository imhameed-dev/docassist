"""Safe handling of uploaded files: size/type checks, hashing, and server-chosen paths.

Nothing here ever uses a client-supplied filename to build a filesystem path.
"""

import hashlib
import os
import re
import sys
import uuid
from pathlib import Path
from typing import BinaryIO

CHUNK_SIZE = 1024 * 1024
PDF_MAGIC = b"%PDF-"
_DOCUMENT_ID = re.compile(r"[0-9a-f]{32}")
MAX_FILENAME_LENGTH = 255
PRIVATE_DIR_MODE = 0o700  # owner only
PRIVATE_FILE_MODE = 0o600  # owner read/write


class UploadError(Exception):
    """Base class for uploads that are rejected before a document is created."""


class EmptyUploadError(UploadError):
    pass


class NotAPdfError(UploadError):
    pass


class UploadTooLargeError(UploadError):
    pass


def new_document_id() -> str:
    """Random, unguessable id. Also the on-disk name, so it never depends on user input."""
    return uuid.uuid4().hex


def stored_path(uploads_dir: Path, document_id: str) -> Path:
    """Path of the stored PDF for a document id. Rejects anything that is not a generated id."""
    if not _DOCUMENT_ID.fullmatch(document_id):
        raise ValueError("invalid document id")
    return uploads_dir / f"{document_id}.pdf"


def clean_filename(raw: str | None) -> str:
    """Make a client-supplied filename safe to *display* (it is never used as a path)."""
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:MAX_FILENAME_LENGTH] or "document.pdf"


def _make_private_dirs(path: Path) -> None:
    """Create `path` and any missing parents as owner-only (0700), whatever the umask.

    mkdir's `mode` is filtered by the process umask and is ignored for parent directories, so
    each directory we create is created individually and then chmod'ed explicitly. Directories
    that already exist are left exactly as they are.
    """
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        try:
            directory.mkdir(mode=PRIVATE_DIR_MODE)
        except FileExistsError:
            continue  # created concurrently by someone else: not ours to change
        directory.chmod(PRIVATE_DIR_MODE)


def save_upload(source: BinaryIO, dest: Path, max_bytes: int) -> tuple[int, str]:
    """Stream `source` to `dest`, enforcing the PDF signature and size limit.

    Returns (size_in_bytes, sha256_hex). On any failure the partial file is removed and the
    exception is re-raised. New directories are created 0700 and the file 0600, independent of
    the process umask.
    """
    _make_private_dirs(dest.parent)
    digest = hashlib.sha256()
    size = 0
    # O_EXCL: fail rather than overwrite. Opened outside the try block on purpose: if the file
    # already exists we must raise without the cleanup below deleting a file we did not create.
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, PRIVATE_FILE_MODE)
    out = os.fdopen(fd, "wb")
    try:
        with out:
            if sys.platform != "win32":
                # The mode passed to os.open is filtered by the umask; set it explicitly.
                os.fchmod(out.fileno(), PRIVATE_FILE_MODE)
            while chunk := source.read(CHUNK_SIZE):
                if size == 0 and not chunk.startswith(PDF_MAGIC):
                    raise NotAPdfError("file does not start with a PDF signature")
                size += len(chunk)
                if size > max_bytes:
                    raise UploadTooLargeError(f"file exceeds {max_bytes} bytes")
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise EmptyUploadError("file is empty")
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return size, digest.hexdigest()
