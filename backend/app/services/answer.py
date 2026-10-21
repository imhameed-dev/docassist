"""Evidence-grounded question answering."""

from sqlalchemy.orm import Session

from app.schemas import AnswerOut, CitationOut
from app.services.answer_provider import AnswerProvider
from app.services.retrieval import SearchResult, search_documents

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I couldn't find relevant evidence in the available document text to answer this question."
)


def _build_citations(passages: list[SearchResult]) -> list[CitationOut]:
    """Create one citation per source document and page."""
    citations: list[CitationOut] = []
    seen: set[tuple[str, int]] = set()

    for passage in passages:
        key = (passage.document_id, passage.page_number)
        if key in seen:
            continue

        seen.add(key)
        citations.append(
            CitationOut(
                document_id=passage.document_id,
                filename=passage.filename,
                page_number=passage.page_number,
                excerpt=passage.text,
            )
        )

    return citations


def answer_question(
    session: Session,
    question: str,
    *,
    provider: AnswerProvider,
    document_id: str | None = None,
    limit: int = 5,
) -> AnswerOut:
    """Answer from retrieved passages and report their exact source pages."""
    passages = search_documents(
        session,
        question,
        document_id=document_id,
        limit=limit,
    )

    if not passages:
        return AnswerOut(
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            insufficient_evidence=True,
            citations=[],
        )

    return AnswerOut(
        answer=provider.generate_answer(question, passages),
        insufficient_evidence=False,
        citations=_build_citations(passages),
    )
