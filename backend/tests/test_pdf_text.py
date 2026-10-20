from pathlib import Path

import pytest

from app.services.pdf_text import PdfProcessingError, clean_text, extract_pdf_text
from tests.pdf_factory import make_encrypted_pdf, make_pdf


def write(tmp_path: Path, data: bytes) -> Path:
    path = tmp_path / "doc.pdf"
    path.write_bytes(data)
    return path


def test_extracts_text_per_page_in_order(tmp_path: Path) -> None:
    result = extract_pdf_text(write(tmp_path, make_pdf(["First page", "Second page"])), 10)
    assert result.page_count == 2
    assert result.pages == ["First page", "Second page"]
    assert result.empty_page_count == 0


def test_text_with_parentheses_and_backslashes_survives(tmp_path: Path) -> None:
    result = extract_pdf_text(write(tmp_path, make_pdf(["Total (net) = 5\\6"])), 10)
    assert result.pages == ["Total (net) = 5\\6"]


def test_pages_without_text_are_counted(tmp_path: Path) -> None:
    result = extract_pdf_text(write(tmp_path, make_pdf(["Has text", None, "More text"])), 10)
    assert result.page_count == 3
    assert result.pages[1] == ""
    assert result.empty_page_count == 1


def test_image_only_pdf_has_no_text_at_all(tmp_path: Path) -> None:
    result = extract_pdf_text(write(tmp_path, make_pdf([None, None])), 10)
    assert result.page_count == 2
    assert result.empty_page_count == 2


def test_garbage_with_pdf_header_is_reported_as_corrupted(tmp_path: Path) -> None:
    path = write(tmp_path, b"%PDF-1.4\nthis is definitely not a real pdf body")
    with pytest.raises(PdfProcessingError) as excinfo:
        extract_pdf_text(path, 10)
    assert excinfo.value.code == "corrupted"


def test_encrypted_pdf_is_reported_as_encrypted(tmp_path: Path) -> None:
    with pytest.raises(PdfProcessingError) as excinfo:
        extract_pdf_text(write(tmp_path, make_encrypted_pdf()), 10)
    assert excinfo.value.code == "encrypted"


def test_page_limit_is_enforced(tmp_path: Path) -> None:
    path = write(tmp_path, make_pdf(["a", "b", "c"]))
    with pytest.raises(PdfProcessingError) as excinfo:
        extract_pdf_text(path, 2)
    assert excinfo.value.code == "too_many_pages"
    assert "3 pages" in excinfo.value.message


def test_clean_text_removes_nul_and_whitespace() -> None:
    assert clean_text("  a\x00b \n") == "ab"
