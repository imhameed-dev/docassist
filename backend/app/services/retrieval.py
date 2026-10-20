"""Page-aware text chunking and keyword retrieval."""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentStatus, Page

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
MIN_TERM_LENGTH = 2


@dataclass(frozen=True)
class TextChunk:
    """A passage that retains its source document and PDF page."""

    document_id: str
    filename: str
    page_number: int
    text: str
    start: int


@dataclass(frozen=True)
class SearchResult:
    """A retrieved passage with a simple keyword relevance score."""

    document_id: str
    filename: str
    page_number: int
    text: str
    score: float


def chunk_text(
    text: str,
    *,
    document_id: str,
    filename: str,
    page_number: int,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[TextChunk]:
    """Split text into overlapping chunks without losing page attribution."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    text = text.strip()
    if not text:
        return []

    chunks: list[TextChunk] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Prefer a nearby word boundary, but avoid tiny chunks when the next
        # whitespace is too close to the beginning of this chunk.
        if end < len(text):
            boundary = text.rfind(" ", start + chunk_size // 2, end)
            if boundary > start:
                end = boundary

        piece = text[start:end].strip()
        if piece:
            chunks.append(
                TextChunk(
                    document_id=document_id,
                    filename=filename,
                    page_number=page_number,
                    text=piece,
                    start=start,
                )
            )

        if end >= len(text):
            break

        # Advance relative to the actual end so the overlap remains bounded.
        start = max(start + 1, end - overlap)

    return chunks


def _terms(text: str) -> set[str]:
    """Normalize query text into searchable word terms."""
    return {term for term in re.findall(r"\w+", text.casefold()) if len(term) >= MIN_TERM_LENGTH}


def search_documents(
    session: Session,
    query: str,
    *,
    document_id: str | None = None,
    limit: int = 5,
) -> list[SearchResult]:
    """Return keyword-matching passages from ready documents, ranked by term coverage."""
    if limit < 1:
        raise ValueError("limit must be positive")

    query_terms = _terms(query)
    if not query_terms:
        return []

    statement = (
        select(Document.id, Document.filename, Page.page_number, Page.text)
        .join(Page, Page.document_id == Document.id)
        .where(Document.status == DocumentStatus.READY.value)
        .order_by(Document.id, Page.page_number)
    )
    if document_id is not None:
        statement = statement.where(Document.id == document_id)

    results: list[SearchResult] = []

    for doc_id, filename, page_number, page_text in session.execute(statement):
        for chunk in chunk_text(
            page_text,
            document_id=doc_id,
            filename=filename,
            page_number=page_number,
        ):
            chunk_terms = _terms(chunk.text)
            matched_terms = query_terms & chunk_terms
            if not matched_terms:
                continue

            # Coverage rewards passages matching more distinct query terms.
            # A small frequency bonus distinguishes repeated mentions.
            coverage = len(matched_terms) / len(query_terms)
            frequency = sum(
                min(len(re.findall(rf"\b{re.escape(term)}\b", chunk.text, re.I)), 3)
                for term in matched_terms
            )
            score = coverage + 0.05 * frequency

            results.append(
                SearchResult(
                    document_id=chunk.document_id,
                    filename=chunk.filename,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    score=score,
                )
            )

    results.sort(key=lambda result: (-result.score, result.document_id, result.page_number))
    return results[:limit]
