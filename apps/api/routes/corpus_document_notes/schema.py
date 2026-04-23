from __future__ import annotations

from packages.schemas.common import BaseSchema


class CorpusCitationItemResponse(BaseSchema):
    """Citation item for corpus notes transport."""

    page_number: int
    snippet: str
    clause_label: str | None = None


class CorpusAnswerNoteResponse(BaseSchema):
    """Answer-plus-citations note block."""

    answer: str | None = None
    citations: list[CorpusCitationItemResponse]


class CorpusChangeSectionResponse(BaseSchema):
    """Change note section with dimensions."""

    answer: str | None = None
    dimensions: list[str]
    citations: list[CorpusCitationItemResponse]


class CorpusQualitySectionResponse(BaseSchema):
    """Quality section for change notes."""

    warnings: list[str]
    citations: list[CorpusCitationItemResponse]


class CorpusChangeKeyClauseResponse(BaseSchema):
    """Change key clause transport model."""

    label: str
    summary: str


class CorpusGoverningNotesResponse(BaseSchema):
    """Typed governing-notes response payload."""

    identity: CorpusAnswerNoteResponse
    parties: CorpusAnswerNoteResponse
    subject: CorpusAnswerNoteResponse
    term: CorpusAnswerNoteResponse
    economics: CorpusAnswerNoteResponse
    controls: CorpusAnswerNoteResponse
    quality: CorpusAnswerNoteResponse


class CorpusChangeNotesResponse(BaseSchema):
    """Typed change-notes response payload."""

    target_artifact: CorpusAnswerNoteResponse
    change: CorpusChangeSectionResponse
    resulting_state: CorpusAnswerNoteResponse
    quality: CorpusQualitySectionResponse
    key_clauses: list[CorpusChangeKeyClauseResponse]


class CorpusDocumentNotesResponse(BaseSchema):
    """Unified notes payload for one document."""

    document_map_type: str | None = None
    governing_notes: CorpusGoverningNotesResponse | None = None
    change_notes: CorpusChangeNotesResponse | None = None
