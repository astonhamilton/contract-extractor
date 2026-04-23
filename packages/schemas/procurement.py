from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from packages.schemas.classification import TernaryLabel
from packages.schemas.common import BaseSchema, ProcessingStatus, StageStatus


class ProcurementCategory(StrEnum):
    PROFESSIONAL_SERVICES = "professional_services"
    SOFTWARE_IT = "software_it"
    MAINTENANCE_OPERATIONS = "maintenance_operations"
    ENGINEERING_CONSTRUCTION = "engineering_construction"
    BEHAVIORAL_HEALTH = "behavioral_health"
    EQUIPMENT = "equipment"
    LEASE = "lease"
    OTHER = "other"


class ProcurementEvidence(BaseSchema):
    """Page-level evidence supporting procurement context inference."""

    label: str
    snippet: str
    page_number: int = Field(ge=1)


class ProcurementContext(BaseSchema):
    """Minimal procurement-context frame shared across later lifecycle reasoning."""

    doc_id: str
    source_filename: str
    is_procurement_doc: TernaryLabel = TernaryLabel.UNCLEAR
    buyer: str | None = None
    seller: str | None = None
    procurement_subject_summary: str | None = None
    procurement_category: ProcurementCategory | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    evidence: list[ProcurementEvidence] = Field(default_factory=list)
    status: StageStatus = Field(default_factory=StageStatus)


class ProcurementContextInput(BaseSchema):
    """Typed input contract for one procurement-context inference request."""

    doc_id: str
    source_filename: str
    model: str
    normalized_document_path: str


class ProcurementContextTrialJudgment(BaseSchema):
    """Human QA template for sampled procurement-context outputs."""

    useful: bool | None = None
    correct_procurement_gate: bool | None = None
    correct_buyer_seller: bool | None = None
    correct_subject_summary: bool | None = None
    correct_category: bool | None = None
    evidence_quality_ok: bool | None = None
    ready_for_pipeline: bool | None = None
    notes: str = ""


def completed_procurement_context_status() -> StageStatus:
    """Return a completed status block for validated procurement-context outputs."""
    return StageStatus(status=ProcessingStatus.COMPLETED)
