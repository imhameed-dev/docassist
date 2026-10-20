"""Document use-cases: upload and process, list, delete."""

import logging
from datetime import UTC, datetime
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Document, DocumentStatus, Page
from app.services.pdf_text import PdfProcessingError, extract_pdf_text
from app.storage import clean_filename, new_document_id, save_upload, stored_path

logger = logging.getLogger(__name__)

NEEDS_OCR_MESSAGE = (
    "No selectable text was found. This PDF is probably scanned or image-only. "
    "OCR is not supported yet, so its contents cannot be searched."
)


def create_document(
    session: Session, settings: Settings, filename: str | None, source: BinaryIO
) -> Document:
    """Store an upload, extract its text, and record the outcome.

    Raises a subclass of storage.UploadError when the upload itself is unacceptable (not a
    PDF, empty, too large); nothing is stored in that case. A PDF that is accepted but cannot
    be processed (corrupted, encrypted, ...) is recorded with status "failed" so the user can
    see why.
    """
    document_id = new_document_id()
    path = stored_path(settings.uploads_dir, document_id)
    size, digest = save_upload(source, path, settings.max_upload_bytes)

    base = {
        "id": document_id,
        "filename": clean_filename(filename),
        "size_bytes": size,
        "sha256": digest,
        "created_at": datetime.now(UTC),
    }
    keep_file = True
    try:
        try:
            extracted = extract_pdf_text(path, settings.max_pages)
        except PdfProcessingError as error:
            keep_file = False  # unusable file: do not keep it on disk
            document = Document(
                **base,
                page_count=0,
                empty_page_count=0,
                status=DocumentStatus.FAILED.value,
                error_code=error.code,
                error_message=error.message,
            )
        else:
            if extracted.empty_page_count == extracted.page_count:
                document = Document(
                    **base,
                    page_count=extracted.page_count,
                    empty_page_count=extracted.empty_page_count,
                    status=DocumentStatus.NEEDS_OCR.value,
                    error_code="needs_ocr",
                    error_message=NEEDS_OCR_MESSAGE,
                )
            else:
                document = Document(
                    **base,
                    page_count=extracted.page_count,
                    empty_page_count=extracted.empty_page_count,
                    status=DocumentStatus.READY.value,
                    error_code=None,
                    error_message=None,
                )
                document.pages = [
                    Page(page_number=number, text=text)
                    for number, text in enumerate(extracted.pages, start=1)
                ]
        session.add(document)
        session.commit()
    except Exception:
        session.rollback()
        path.unlink(missing_ok=True)
        raise

    if not keep_file:
        path.unlink(missing_ok=True)
    return document


def list_documents(session: Session) -> list[Document]:
    return list(session.scalars(select(Document).order_by(Document.created_at.desc())))


def get_document(session: Session, document_id: str) -> Document | None:
    return session.get(Document, document_id)


def delete_document(session: Session, settings: Settings, document_id: str) -> bool:
    """Delete a document, its extracted pages, and its stored file. False if not found."""
    document = session.get(Document, document_id)
    if document is None:
        return False
    session.delete(document)
    session.commit()
    try:
        stored_path(settings.uploads_dir, document_id).unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove stored file for deleted document %s", document_id)
    return True
