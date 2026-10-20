"""Extract text from PDFs with pypdf.

Pure functions: no database or web dependencies, so they are easy to test on their own.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class PdfProcessingError(Exception):
    """The PDF was accepted as an upload but could not be processed.

    `code` is a stable machine-readable reason; `message` is safe to show to the user.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ExtractedPdf:
    pages: list[str]  # pages[0] is page 1

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def empty_page_count(self) -> int:
        """Pages with no extractable text (blank, or images only)."""
        return sum(1 for text in self.pages if not text)


def clean_text(text: str) -> str:
    """Remove NUL characters (rejected by PostgreSQL) and surrounding whitespace."""
    return text.replace("\x00", "").strip()


def extract_pdf_text(path: Path, max_pages: int) -> ExtractedPdf:
    """Return the text of each page, or raise PdfProcessingError with a specific reason."""
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise PdfProcessingError(
                "encrypted",
                "This PDF is password-protected or encrypted. Remove the protection and "
                "upload it again.",
            )
        page_count = len(reader.pages)
        if page_count == 0:
            raise PdfProcessingError("no_pages", "This PDF contains no pages.")
        if page_count > max_pages:
            raise PdfProcessingError(
                "too_many_pages",
                f"This PDF has {page_count} pages; the limit is {max_pages}.",
            )
        pages = [clean_text(page.extract_text() or "") for page in reader.pages]
    except PdfProcessingError:
        raise
    except Exception as exc:
        # pypdf can raise many different exception types on malformed, untrusted input.
        # Whatever it was, the file is unusable; log the type (never the content) and report it.
        logger.warning("PDF could not be parsed (%s)", type(exc).__name__)
        raise PdfProcessingError(
            "corrupted", "This PDF is corrupted or could not be read."
        ) from exc
    return ExtractedPdf(pages=pages)
