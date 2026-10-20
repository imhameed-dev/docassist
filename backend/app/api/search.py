"""HTTP endpoint for searching extracted document passages."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Path as PathParam
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import SearchResultOut
from app.services.retrieval import search_documents

router = APIRouter(prefix="/api/documents", tags=["search"])

SessionDep = Annotated[Session, Depends(get_session)]
DocumentId = Annotated[str, PathParam(pattern=r"^[0-9a-f]{32}$")]


@router.get("/search", response_model=list[SearchResultOut])
def search(
    session: SessionDep,
    q: Annotated[str, Query(min_length=1, max_length=500)],
    document_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[SearchResultOut]:
    """Search ready documents and return passages with page attribution."""
    if document_id is not None and not __import__("re").fullmatch(r"[0-9a-f]{32}", document_id):
        raise HTTPException(status_code=422, detail="Invalid document ID.")

    results = search_documents(
        session,
        q,
        document_id=document_id,
        limit=limit,
    )
    return [SearchResultOut.model_validate(result.__dict__) for result in results]
