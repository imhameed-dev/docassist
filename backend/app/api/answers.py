"""HTTP endpoint for evidence-grounded answers."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import AnswerOut, AnswerRequest
from app.services.answer import answer_question
from app.services.answer_provider import AnswerProvider, MockAnswerProvider

router = APIRouter(prefix="/api", tags=["answers"])

SessionDep = Annotated[Session, Depends(get_session)]


def get_answer_provider() -> AnswerProvider:
    """Return the default provider, which makes no external API calls."""
    return MockAnswerProvider()


ProviderDep = Annotated[AnswerProvider, Depends(get_answer_provider)]


@router.post("/answer", response_model=AnswerOut)
def answer(request: AnswerRequest, session: SessionDep, provider: ProviderDep) -> AnswerOut:
    """Answer a question using retrieved document passages and page citations."""
    return answer_question(
        session,
        request.question,
        provider=provider,
        document_id=request.document_id,
        limit=request.limit,
    )
