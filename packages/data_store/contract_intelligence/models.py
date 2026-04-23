from __future__ import annotations

from pydantic import Field

from packages.schemas.common import BaseSchema


class DocumentRecord(BaseSchema):
    """Core document metadata row from the contract-intelligence DB."""

    doc_id: str
    source_filename: str
    source_pdf_path: str
    source_pdf_size_bytes: int | None = None
    sha256: str | None = None
    page_count: int
    has_text_layer: bool | None = None
    quality_flags: list[str] = Field(default_factory=list)
    processing_status: str | None = None
    normalized_document_path: str | None = None


class ProcurementContextRecord(BaseSchema):
    """Procurement-context row shaped for assistant reads."""

    doc_id: str
    is_procurement_related: bool | None = None
    buyer: str | None = None
    seller: str | None = None
    what_is_being_bought: str | None = None
    procurement_category: str | None = None
    context_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)
    confidence: float | None = None


class ClassificationRecord(BaseSchema):
    """Document classification row shaped for assistant reads."""

    doc_id: str
    procurement_stage: str
    primary_document_role: str
    change_kind: str | None = None
    confidence: float
    rationale: str = ""
    evidence_pages: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CitationRecord(BaseSchema):
    """Flattened citation row."""

    page_number: int
    snippet: str
    stage: str
    domain: str
    clause_label: str | None = None
    ordinal: int = 0


class GoverningNotesRecord(BaseSchema):
    """Flattened governing-notes row plus citations."""

    doc_id: str
    identity_answer: str | None = None
    parties_answer: str | None = None
    subject_answer: str | None = None
    term_answer: str | None = None
    economics_answer: str | None = None
    controls_answer: str | None = None
    quality_warnings: list[str] = Field(default_factory=list)
    confidence: float | None = None
    citations: list[CitationRecord] = Field(default_factory=list)


class ChangeKeyClauseRecord(BaseSchema):
    """Flattened change key clause."""

    label: str
    summary: str
    ordinal: int = 0


class ChangeNotesRecord(BaseSchema):
    """Flattened change-notes row plus clauses/citations."""

    doc_id: str
    target_artifact_answer: str | None = None
    change_answer: str | None = None
    resulting_state_answer: str | None = None
    dimensions: list[str] = Field(default_factory=list)
    quality_warnings: list[str] = Field(default_factory=list)
    confidence: float | None = None
    key_clauses: list[ChangeKeyClauseRecord] = Field(default_factory=list)
    citations: list[CitationRecord] = Field(default_factory=list)


class PageRecord(BaseSchema):
    """Best page-content row."""

    doc_id: str
    page_number: int
    content: str
    representation: str | None = None
    source_path: str | None = None
    extraction_method: str | None = None
    char_count: int = 0
    ocr_char_count: int = 0
    ocr_confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    estimated_tokens: int = 0


class PageVariantRecord(PageRecord):
    """All available normalized variants for one page."""

    priority: int


class PageNoteRecord(BaseSchema):
    """Page-note row."""

    doc_id: str
    page_number: int
    page_role: str | None = None
    summary: str
    key_terms: list[str] = Field(default_factory=list)
    relevance_tags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DocumentIndexItem(BaseSchema):
    """Lightweight document listing item for search/index screens and tools."""

    doc_id: str
    source_filename: str
    page_count: int = 0
    buyer: str | None = None
    seller: str | None = None
    what_is_being_bought: str | None = None
    procurement_category: str | None = None
    procurement_stage: str | None = None
    primary_document_role: str | None = None
    change_kind: str | None = None
    document_map_type: str | None = None
    governing_summary: str | None = None
    change_summary: str | None = None
    has_governing_notes: bool = False
    has_change_notes: bool = False
    has_page_notes: bool = False


class DocumentAggregate(BaseSchema):
    """Document-centered aggregate returned by the main document query surface."""

    document: DocumentRecord
    procurement_context: ProcurementContextRecord | None = None
    classification: ClassificationRecord | None = None
    governing_notes: GoverningNotesRecord | None = None
    change_notes: ChangeNotesRecord | None = None
    page_notes: list[PageNoteRecord] = Field(default_factory=list)
