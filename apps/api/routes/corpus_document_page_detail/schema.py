from __future__ import annotations

from packages.schemas.common import BaseSchema


class CorpusDocumentPageDetailPageResponse(BaseSchema):
    """Single page metadata block."""

    page_number: int
    best_representation: str | None = None
    available_representations: list[str]
    estimated_tokens: int
    preview: str = ""
    page_note_available: bool = False


class CorpusDocumentPageDetailContentResponse(BaseSchema):
    """One page content block."""

    representation: str | None = None
    source_path: str | None = None
    content: str
    extraction_method: str | None = None
    char_count: int
    ocr_confidence: float | None = None
    warnings: list[str]
    quality_flags: list[str]
    estimated_tokens: int
    priority: int | None = None
    page_role: str | None = None
    key_terms: list[str]
    relevance_tags: list[str]


class CorpusDocumentPageDetailResponse(BaseSchema):
    """Full single-page response."""

    page: CorpusDocumentPageDetailPageResponse
    best_content: CorpusDocumentPageDetailContentResponse
    variants: list[CorpusDocumentPageDetailContentResponse]
