from __future__ import annotations

from packages.schemas.common import BaseSchema


class CorpusSummary(BaseSchema):
    """Application-layer summary of the corpus browser dataset."""

    document_count: int
    db_size_mb: float
    raw_corpus_size_mb: float


class CorpusDocumentListItem(BaseSchema):
    """Application-layer list item for the corpus browser."""

    doc_id: str
    source_filename: str
    title: str
    overview: str = ""
    page_count: int = 0
    buyer: str | None = None
    seller: str | None = None
    procurement_stage: str | None = None
    primary_document_role: str | None = None
    document_map_type: str | None = None


class CorpusDocumentsPage(BaseSchema):
    """Paginated corpus browser page."""

    items: list[CorpusDocumentListItem]
    total: int
    page: int
    page_size: int
    sort: str
    query: str = ""


class CorpusDocumentDetail(BaseSchema):
    """Initial selected-document detail for the corpus browser."""

    document: dict[str, object]
    overview: dict[str, object]
    procurement_context: dict[str, object]
    classification: dict[str, object]


class CorpusPageNoteItem(BaseSchema):
    """Application-layer cliff-note item for one page."""

    page_number: int
    page_role: str | None = None
    summary: str
    key_terms: list[str]
    relevance_tags: list[str]
    warnings: list[str]


class CorpusDocumentPageNotesPage(BaseSchema):
    """Paginated page-notes page for one document."""

    items: list[CorpusPageNoteItem]
    total: int
    page: int
    page_size: int


class CorpusPageListItem(BaseSchema):
    """Application-layer page tile item for one document page."""

    page_number: int
    best_representation: str | None = None
    available_representations: list[str]
    estimated_tokens: int = 0
    preview: str = ""
    page_note_available: bool = False


class CorpusDocumentPagesPage(BaseSchema):
    """Paginated pages index for one document."""

    items: list[CorpusPageListItem]
    total: int
    page: int
    page_size: int


class CorpusPageContent(BaseSchema):
    """Full content block for one page representation."""

    representation: str | None = None
    source_path: str | None = None
    content: str
    extraction_method: str | None = None
    char_count: int = 0
    ocr_confidence: float | None = None
    warnings: list[str]
    quality_flags: list[str]
    estimated_tokens: int = 0
    priority: int | None = None
    page_role: str | None = None
    key_terms: list[str] = []
    relevance_tags: list[str] = []


class CorpusDocumentPageDetail(BaseSchema):
    """Single-page detail for one document page."""

    page: CorpusPageListItem
    best_content: CorpusPageContent
    variants: list[CorpusPageContent]


class CorpusCitationItem(BaseSchema):
    """Citation item for corpus note payloads."""

    page_number: int
    snippet: str
    clause_label: str | None = None


class CorpusAnswerNote(BaseSchema):
    """Answer-plus-citations note block."""

    answer: str | None = None
    citations: list[CorpusCitationItem]


class CorpusChangeKeyClause(BaseSchema):
    """Change key clause for corpus notes."""

    label: str
    summary: str


class CorpusChangeSection(BaseSchema):
    """Change note section with dimensions."""

    answer: str | None = None
    dimensions: list[str]
    citations: list[CorpusCitationItem]


class CorpusQualitySection(BaseSchema):
    """Quality/warnings section for change notes."""

    warnings: list[str]
    citations: list[CorpusCitationItem]


class CorpusGoverningNotes(BaseSchema):
    """Application-layer governing notes payload."""

    identity: CorpusAnswerNote
    parties: CorpusAnswerNote
    subject: CorpusAnswerNote
    term: CorpusAnswerNote
    economics: CorpusAnswerNote
    controls: CorpusAnswerNote
    quality: CorpusAnswerNote


class CorpusChangeNotes(BaseSchema):
    """Application-layer change notes payload."""

    target_artifact: CorpusAnswerNote
    change: CorpusChangeSection
    resulting_state: CorpusAnswerNote
    quality: CorpusQualitySection
    key_clauses: list[CorpusChangeKeyClause]


class CorpusDocumentNotes(BaseSchema):
    """Unified corpus notes payload for one document."""

    document_map_type: str | None = None
    governing_notes: CorpusGoverningNotes | None = None
    change_notes: CorpusChangeNotes | None = None
