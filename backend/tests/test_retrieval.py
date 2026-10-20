"""Tests for page-aware chunking and keyword retrieval."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.models import Document, DocumentStatus, Page
from app.services.retrieval import chunk_text, search_documents


def test_chunk_text_preserves_source_and_page() -> None:
    chunks = chunk_text(
        "alpha beta gamma delta epsilon",
        document_id="a" * 32,
        filename="report.pdf",
        page_number=4,
        chunk_size=16,
        overlap=4,
    )

    assert len(chunks) > 1
    assert all(chunk.document_id == "a" * 32 for chunk in chunks)
    assert all(chunk.filename == "report.pdf" for chunk in chunks)
    assert all(chunk.page_number == 4 for chunk in chunks)
    assert chunks[0].text.startswith("alpha")


def test_chunk_text_empty_and_validation() -> None:
    assert (
        chunk_text(
            "  ",
            document_id="a" * 32,
            filename="empty.pdf",
            page_number=1,
        )
        == []
    )

    with pytest.raises(ValueError):
        chunk_text(
            "text",
            document_id="a" * 32,
            filename="x.pdf",
            page_number=1,
            chunk_size=0,
        )

    with pytest.raises(ValueError):
        chunk_text(
            "text",
            document_id="a" * 32,
            filename="x.pdf",
            page_number=1,
            chunk_size=10,
            overlap=10,
        )


def add_document(
    session: Session,
    document_id: str,
    filename: str,
    status: str,
    pages: list[str],
) -> None:
    document = Document(
        id=document_id,
        filename=filename,
        size_bytes=100,
        sha256="0" * 64,
        page_count=len(pages),
        empty_page_count=sum(not text.strip() for text in pages),
        status=status,
        error_code=None,
        error_message=None,
        created_at=datetime.now(UTC),
    )
    document.pages = [
        Page(page_number=number, text=text) for number, text in enumerate(pages, start=1)
    ]
    session.add(document)
    session.commit()


def test_search_returns_page_citations_and_ranks_matches(engine) -> None:
    with Session(engine) as session:
        add_document(
            session,
            "a" * 32,
            "alpha.pdf",
            DocumentStatus.READY.value,
            [
                "A short introduction about gardens.",
                "The secure document retrieval system searches relevant passages.",
                "Unrelated notes about cooking.",
            ],
        )

        results = search_documents(session, "secure document retrieval")

    assert results
    assert results[0].document_id == "a" * 32
    assert results[0].filename == "alpha.pdf"
    assert results[0].page_number == 2
    assert "retrieval" in results[0].text
    assert results[0].score > 0


def test_search_can_be_restricted_to_one_document(engine) -> None:
    with Session(engine) as session:
        add_document(
            session,
            "a" * 32,
            "first.pdf",
            DocumentStatus.READY.value,
            ["Project keyword appears here."],
        )
        add_document(
            session,
            "b" * 32,
            "second.pdf",
            DocumentStatus.READY.value,
            ["Project keyword appears here too."],
        )

        results = search_documents(session, "project keyword", document_id="b" * 32)

    assert results
    assert {result.document_id for result in results} == {"b" * 32}
    assert {result.filename for result in results} == {"second.pdf"}


def test_search_skips_documents_not_ready(engine) -> None:
    with Session(engine) as session:
        add_document(
            session,
            "a" * 32,
            "scanned.pdf",
            DocumentStatus.NEEDS_OCR.value,
            ["Secret searchable phrase."],
        )

        assert search_documents(session, "searchable phrase") == []


def test_search_handles_empty_queries_and_no_matches(engine) -> None:
    with Session(engine) as session:
        assert search_documents(session, "   ") == []
        assert search_documents(session, "a I") == []
        assert search_documents(session, "not-present") == []


def test_search_validates_limit(engine) -> None:
    with Session(engine) as session, pytest.raises(ValueError):
        search_documents(session, "anything", limit=0)
