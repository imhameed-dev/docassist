"""Response models for the API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    size_bytes: int
    page_count: int
    empty_page_count: int
    status: Literal["ready", "needs_ocr", "failed"]
    error_code: str | None
    error_message: str | None
    created_at: datetime


class SearchResultOut(BaseModel):
    """A retrieved passage with its source and relevance score."""

    document_id: str
    filename: str
    page_number: int
    text: str
    score: float


class AnswerRequest(BaseModel):
    """A question to answer using the user's uploaded documents."""

    question: str = Field(min_length=1, max_length=500)
    document_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    limit: int = Field(default=5, ge=1, le=10)


class CitationOut(BaseModel):
    """A source passage supporting an answer."""

    document_id: str
    filename: str
    page_number: int
    excerpt: str


class AnswerOut(BaseModel):
    """An evidence-grounded answer, or an explicit insufficient-evidence result."""

    answer: str
    insufficient_evidence: bool
    citations: list[CitationOut]
