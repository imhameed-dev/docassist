"""HTTP endpoints for managing documents."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi import Path as PathParam
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.schemas import DocumentOut
from app.services import documents as service
from app.storage import EmptyUploadError, NotAPdfError, UploadTooLargeError

router = APIRouter(prefix="/api/documents", tags=["documents"])

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
DocumentId = Annotated[str, PathParam(pattern=r"^[0-9a-f]{32}$")]


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(file: UploadFile, session: SessionDep, settings: SettingsDep) -> DocumentOut:
    try:
        document = service.create_document(session, settings, file.filename, file.file)
    except EmptyUploadError:
        raise _error(400, "empty_file", "The uploaded file is empty.") from None
    except NotAPdfError:
        raise _error(415, "not_a_pdf", "The file is not a valid PDF.") from None
    except UploadTooLargeError:
        raise _error(
            413, "file_too_large", f"The file is larger than the {settings.max_upload_mb} MB limit."
        ) from None
    return DocumentOut.model_validate(document)


@router.get("", response_model=list[DocumentOut])
def list_documents(session: SessionDep) -> list[DocumentOut]:
    return [DocumentOut.model_validate(d) for d in service.list_documents(session)]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: DocumentId, session: SessionDep) -> DocumentOut:
    document = service.get_document(session, document_id)
    if document is None:
        raise _error(404, "not_found", "Document not found.")
    return DocumentOut.model_validate(document)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: DocumentId, session: SessionDep, settings: SettingsDep) -> None:
    if not service.delete_document(session, settings, document_id):
        raise _error(404, "not_found", "Document not found.")
