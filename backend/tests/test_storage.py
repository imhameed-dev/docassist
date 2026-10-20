import contextlib
import hashlib
import io
import os
import stat
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.storage import (
    EmptyUploadError,
    NotAPdfError,
    UploadTooLargeError,
    clean_filename,
    new_document_id,
    save_upload,
    stored_path,
)

PDF_BYTES = b"%PDF-1.4\n" + b"x" * 100


def test_save_upload_writes_file_and_returns_size_and_hash(tmp_path: Path) -> None:
    dest = tmp_path / "uploads" / "a.pdf"
    size, digest = save_upload(io.BytesIO(PDF_BYTES), dest, max_bytes=1000)
    assert size == len(PDF_BYTES)
    assert digest == hashlib.sha256(PDF_BYTES).hexdigest()
    assert dest.read_bytes() == PDF_BYTES


def test_non_pdf_is_rejected_and_nothing_is_left_behind(tmp_path: Path) -> None:
    dest = tmp_path / "a.pdf"
    with pytest.raises(NotAPdfError):
        save_upload(io.BytesIO(b"MZ\x90\x00 an executable pretending to be a pdf"), dest, 1000)
    assert not dest.exists()


def test_empty_upload_is_rejected(tmp_path: Path) -> None:
    dest = tmp_path / "a.pdf"
    with pytest.raises(EmptyUploadError):
        save_upload(io.BytesIO(b""), dest, 1000)
    assert not dest.exists()


def test_oversized_upload_is_rejected_and_removed(tmp_path: Path) -> None:
    dest = tmp_path / "a.pdf"
    with pytest.raises(UploadTooLargeError):
        save_upload(io.BytesIO(PDF_BYTES), dest, max_bytes=50)
    assert not dest.exists()


def test_existing_file_is_never_overwritten(tmp_path: Path) -> None:
    dest = tmp_path / "a.pdf"
    dest.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        save_upload(io.BytesIO(PDF_BYTES), dest, 1000)
    assert dest.read_bytes() == b"original"  # untouched, not deleted by cleanup


def test_stored_path_accepts_generated_ids(tmp_path: Path) -> None:
    document_id = new_document_id()
    assert stored_path(tmp_path, document_id) == tmp_path / f"{document_id}.pdf"


def test_stored_path_rejects_anything_else(tmp_path: Path) -> None:
    for bad in ["../etc/passwd", "a" * 31, "A" * 32, "a" * 32 + "/..", "", "..", "a/b"]:
        with pytest.raises(ValueError):
            stored_path(tmp_path, bad)


def test_clean_filename_strips_directories_and_control_characters() -> None:
    assert clean_filename("../../etc/evil.pdf") == "evil.pdf"
    assert clean_filename("C:\\Users\\me\\report.pdf") == "report.pdf"
    assert clean_filename("bad\nname\x00.pdf") == "badname.pdf"
    assert clean_filename(None) == "document.pdf"
    assert clean_filename("   ") == "document.pdf"
    assert len(clean_filename("x" * 1000)) == 255


# --- Permissions -------------------------------------------------------------------------
# These check the actual mode bits under several umasks, so they cannot pass just because the
# environment happens to have a convenient default.

posix_only = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX permission bits are not meaningful on Windows"
)

# 000: nothing masked. 022: the usual default. 277: strips the owner's write bit, which breaks
# anything that relies on the umask to produce the right mode.
UMASKS = (0o000, 0o022, 0o277)


@contextlib.contextmanager
def umask(value: int) -> Iterator[None]:
    previous = os.umask(value)
    try:
        yield
    finally:
        os.umask(previous)


def mode_of(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


@posix_only
def test_uploaded_file_is_owner_read_write_only_whatever_the_umask(tmp_path: Path) -> None:
    for mask in UMASKS:
        dest = tmp_path / f"{mask:03o}" / "a.pdf"
        with umask(mask):
            save_upload(io.BytesIO(PDF_BYTES), dest, max_bytes=1000)
        assert mode_of(dest) == 0o600, f"umask {mask:03o}"


@posix_only
def test_new_upload_directories_are_owner_only_whatever_the_umask(tmp_path: Path) -> None:
    for mask in UMASKS:
        root = tmp_path / f"{mask:03o}"
        dest = root / "data" / "uploads" / "a.pdf"  # three directory levels, all new
        with umask(mask):
            save_upload(io.BytesIO(PDF_BYTES), dest, max_bytes=1000)
        for directory in (root, root / "data", root / "data" / "uploads"):
            assert mode_of(directory) == 0o700, f"{directory.name} with umask {mask:03o}"


@posix_only
def test_existing_directories_keep_their_permissions(tmp_path: Path) -> None:
    existing = tmp_path / "data"
    existing.mkdir()
    existing.chmod(0o755)
    dest = existing / "uploads" / "a.pdf"
    save_upload(io.BytesIO(PDF_BYTES), dest, max_bytes=1000)
    assert mode_of(existing) == 0o755  # not created by us, so not changed
    assert mode_of(existing / "uploads") == 0o700
