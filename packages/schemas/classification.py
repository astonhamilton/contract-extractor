from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from packages.schemas.common import BaseSchema, ProcessingStatus, StageStatus


class ProcurementStage(StrEnum):
    SOURCING = "sourcing"
    AWARD = "award"
    CONTRACTING = "contracting"
    ACTIVE_CHANGE = "active_change"
    COMPLIANCE = "compliance"
    UNCLEAR = "unclear"


class DocumentRole(StrEnum):
    OPERATIVE = "operative"
    DELTA = "delta"
    CONTEXT = "context"


class DocumentKind(StrEnum):
    """Deprecated compatibility enum for old routing language."""

    GOVERNING = "governing"
    CHANGE = "change"
    SUPPORTING = "supporting"


class ChangeKind(StrEnum):
    RENEWAL = "renewal"
    AMENDMENT = "amendment"
    PRICING_UPDATE = "pricing_update"


class TernaryLabel(StrEnum):
    YES = "yes"
    NO = "no"
    UNCLEAR = "unclear"


class BinaryLabel(StrEnum):
    YES = "yes"
    NO = "no"


class ClassificationEvidence(BaseSchema):
    label: str
    snippet: str
    page_number: int = Field(ge=1)


class DocumentClassificationInput(BaseSchema):
    doc_id: str
    source_filename: str
    model: str
    normalized_document_path: str


class DocumentClassification(BaseSchema):
    doc_id: str
    source_filename: str
    procurement_stage: ProcurementStage
    primary_document_role: DocumentRole
    change_kind: ChangeKind | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_pages: list[int] = Field(default_factory=list)
    rationale: str = ""
    warnings: list[str] = Field(default_factory=list)
    evidence: list[ClassificationEvidence] = Field(default_factory=list)
    status: StageStatus = Field(default_factory=StageStatus)

    @property
    def document_kind(self) -> DocumentKind | None:
        """Return the old routing taxonomy for compatibility with downstream code."""
        if self.primary_document_role == DocumentRole.OPERATIVE and self.procurement_stage == ProcurementStage.CONTRACTING:
            return DocumentKind.GOVERNING
        if self.primary_document_role == DocumentRole.DELTA and self.procurement_stage == ProcurementStage.ACTIVE_CHANGE:
            return DocumentKind.CHANGE
        if self.primary_document_role == DocumentRole.CONTEXT:
            return DocumentKind.SUPPORTING
        return None

    @property
    def document_role(self) -> DocumentRole:
        """Compatibility alias for older call sites."""
        return self.primary_document_role

    @property
    def routes_to_governing_domain_notes(self) -> bool:
        """Return whether this classification should route to governing domain notes."""
        return (
            self.procurement_stage == ProcurementStage.CONTRACTING
            and self.primary_document_role == DocumentRole.OPERATIVE
        )

    @property
    def routes_to_change_extraction(self) -> bool:
        """Return whether this classification should route to change extraction."""
        return (
            self.procurement_stage == ProcurementStage.ACTIVE_CHANGE
            and self.primary_document_role == DocumentRole.DELTA
        )


class DocumentClassificationTrialJudgment(BaseSchema):
    useful: bool | None = None
    correct_procurement_stage: bool | None = None
    correct_document_role: bool | None = None
    correct_change_kind: bool | None = None
    evidence_quality_ok: bool | None = None
    ready_for_pipeline: bool | None = None
    notes: str = ""


def completed_classification_status() -> StageStatus:
    """Return a completed status block for validated classification outputs."""
    return StageStatus(status=ProcessingStatus.COMPLETED)
