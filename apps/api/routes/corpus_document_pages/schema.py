from __future__ import annotations

from pydantic import Field

from packages.schemas.common import BaseSchema


class CorpusDocumentPagesQuery(BaseSchema):
    """Validated pages query params."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class CorpusDocumentPageResponse(BaseSchema):
    """One page tile item for the corpus browser."""

    page_number: int
    best_representation: str | None = None
    available_representations: list[str]
    estimated_tokens: int
    preview: str = ""
    page_note_available: bool = False


class CorpusDocumentPagesResponse(BaseSchema):
    """Paginated page-index response for one document."""

    items: list[CorpusDocumentPageResponse]
    total: int
    page: int
    page_size: int
