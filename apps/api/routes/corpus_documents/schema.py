from __future__ import annotations

from typing import Literal

from pydantic import Field

from packages.schemas.common import BaseSchema


class CorpusDocumentsQuery(BaseSchema):
    """Validated corpus list query params."""

    q: str = ""
    sort: Literal["name", "page_count", "seller", "buyer"] = "name"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class CorpusDocumentListItemResponse(BaseSchema):
    """One corpus-browser list row."""

    doc_id: str
    source_filename: str
    title: str
    overview: str = ""
    page_count: int
    buyer: str | None = None
    seller: str | None = None
    procurement_stage: str | None = None
    primary_document_role: str | None = None
    document_map_type: str | None = None


class CorpusDocumentsResponse(BaseSchema):
    """Paginated corpus-browser response."""

    items: list[CorpusDocumentListItemResponse]
    total: int
    page: int
    page_size: int
