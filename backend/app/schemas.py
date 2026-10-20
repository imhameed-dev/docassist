"""Response models for the API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


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
