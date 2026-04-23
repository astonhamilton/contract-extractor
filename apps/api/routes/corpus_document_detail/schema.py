from __future__ import annotations

from packages.schemas.common import BaseSchema


class CorpusDocumentDetailDocumentResponse(BaseSchema):
    """Document identity block for the selected-document response."""

    doc_id: str
    title: str
    source_filename: str
    page_count: int


class CorpusDocumentDetailOverviewResponse(BaseSchema):
    """Overview block for the selected-document response."""

    summary: str = ""
    document_map_type: str | None = None
    supports_page_notes: bool = False


class CorpusDocumentDetailProcurementContextResponse(BaseSchema):
    """Procurement-context block for the selected-document response."""

    buyer: str | None = None
    seller: str | None = None
    what_is_being_bought: str | None = None
    procurement_category: str | None = None


class CorpusDocumentDetailClassificationResponse(BaseSchema):
    """Classification block for the selected-document response."""

    procurement_stage: str | None = None
    primary_document_role: str | None = None
    change_kind: str | None = None


class CorpusDocumentDetailResponse(BaseSchema):
    """Initial selected-document response for the corpus browser."""

    document: CorpusDocumentDetailDocumentResponse
    overview: CorpusDocumentDetailOverviewResponse
    procurement_context: CorpusDocumentDetailProcurementContextResponse
    classification: CorpusDocumentDetailClassificationResponse
