from __future__ import annotations

from pydantic import Field

from packages.schemas.common import BaseSchema


class CorpusDocumentPageNotesQuery(BaseSchema):
    """Validated page-notes query params."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class CorpusDocumentPageNoteResponse(BaseSchema):
    """One page-note item for the corpus browser."""

    page_number: int
    page_role: str | None = None
    summary: str
    key_terms: list[str]
    relevance_tags: list[str]
    warnings: list[str]


class CorpusDocumentPageNotesResponse(BaseSchema):
    """Paginated page-notes response."""

    items: list[CorpusDocumentPageNoteResponse]
    total: int
    page: int
    page_size: int
