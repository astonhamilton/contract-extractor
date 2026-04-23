from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from enum import StrEnum
from functools import lru_cache
import re

from pydantic import Field, create_model, field_validator, model_validator

from packages.schemas.common import BaseSchema, ProcessingStatus, StageStatus
from packages.schemas.classification import ChangeKind


class FieldValueType(StrEnum):
    STRING = "string"
    DATE = "date"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    JSON = "json"


class LifecycleEventType(StrEnum):
    AWARD = "award"
    EXECUTION = "execution"
    RENEWAL = "renewal"
    MODIFICATION = "modification"
    PRICE_CHANGE = "price_change"
    DISCLOSURE = "disclosure"


class ChangeDimension(StrEnum):
    TERM = "term"
    PRICING = "pricing"
    SCOPE = "scope"
    CONTROL = "control"
    OTHER = "other"


class Citation(BaseSchema):
    page_number: int = Field(ge=1)
    snippet: str


class PageRole(StrEnum):
    OPERATIVE_CLAUSE = "operative_clause"
    CHANGE_CLAUSE = "change_clause"
    PRICING_OR_RATE_TABLE = "pricing_or_rate_table"
    SIGNATURE_OR_EXECUTION = "signature_or_execution"
    COMPLIANCE_OR_DISCLOSURE = "compliance_or_disclosure"
    SUPPORTING_CONTEXT = "supporting_context"
    COVER_OR_INDEX = "cover_or_index"
    LOW_VALUE_OR_BOILERPLATE = "low_value_or_boilerplate"
    UNCLEAR = "unclear"


class PageRelevanceTag(StrEnum):
    GOVERNING = "governing"
    CHANGE = "change"
    PRICING = "pricing"
    TERM = "term"
    PARTIES = "parties"
    COMPLIANCE = "compliance"
    PROCUREMENT_HISTORY = "procurement_history"
    SIGNATURE = "signature"
    LOW_VALUE = "low_value"


class MoneyAmount(BaseSchema):
    """A normalized money value plus the raw clause text when helpful."""

    amount: float | None = None
    currency: str | None = None
    text: str | None = None


class Party(BaseSchema):
    """A named party captured from the governing document."""

    name: str
    role: str | None = None
    note: str | None = None


class RateCardItem(BaseSchema):
    """One extracted rate, fee, or unit-price entry."""

    label: str
    amount: float | None = None
    currency: str | None = None
    unit: str | None = None
    text: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class ContractReference(BaseSchema):
    """A typed reference connected to the governing artifact."""

    ref_type: str
    value: str
    note: str | None = None


class GoverningIdentity(BaseSchema):
    """Identity and linkage information for the governing artifact."""

    title: str | None = None
    artifact_type: str | None = None
    primary_identifier: str | None = None
    references: list[ContractReference] = Field(default_factory=list)


class GoverningParties(BaseSchema):
    """Principal contract-side organizations for the governing artifact."""

    public_party: Party | None = None
    counterparty: Party | None = None
    other_entities: list[Party] = Field(default_factory=list)


class GoverningSubject(BaseSchema):
    """What the governing artifact is actually buying or governing."""

    summary: str | None = None
    scope_text: str | None = None
    deliverables: list[str] = Field(default_factory=list)
    service_locations: list[str] = Field(default_factory=list)


class GoverningTerm(BaseSchema):
    """Term and renewal semantics for the governing artifact."""

    execution_date: date | None = None
    effective_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    renewal_structure: str | None = None
    renewal_text: str | None = None


class GoverningEconomics(BaseSchema):
    """Commercial structure and pricing for the governing artifact."""

    pricing_model: str | None = None
    contract_value: MoneyAmount | None = None
    capped_value: MoneyAmount | None = None
    payment_terms: str | None = None
    pricing_schedule: list[RateCardItem] = Field(default_factory=list)


class GoverningControls(BaseSchema):
    """Key operating controls, constraints, and compliance duties."""

    termination_for_convenience: bool | None = None
    termination_for_cause: bool | None = None
    notice_period_days: int | None = Field(default=None, ge=0)
    insurance_requirements: str | None = None
    performance_requirements: str | None = None
    compliance_requirements: list[str] = Field(default_factory=list)


class GoverningEvidence(BaseSchema):
    """Quality metadata and evidence supporting the extraction."""

    extraction_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class DomainNote(BaseSchema):
    """One answer-shaped note with supporting citations."""

    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class IdentityNotes(BaseSchema):
    """Question-shaped notes about governing artifact identity."""

    what_this_document_is: DomainNote = Field(default_factory=DomainNote)
    how_it_identifies_itself: DomainNote = Field(default_factory=DomainNote)
    linked_documents_or_materials: DomainNote = Field(default_factory=DomainNote)


class PartiesNotes(BaseSchema):
    """Question-shaped notes about the main contracting parties."""

    who_the_main_parties_are: DomainNote = Field(default_factory=DomainNote)
    how_their_roles_are_described: DomainNote = Field(default_factory=DomainNote)
    other_material_entities: DomainNote = Field(default_factory=DomainNote)


class SubjectNotes(BaseSchema):
    """Question-shaped notes about what is being bought or governed."""

    what_is_being_bought_or_governed: DomainNote = Field(default_factory=DomainNote)
    what_scope_or_deliverables_are_described: DomainNote = Field(
        default_factory=DomainNote
    )


class TermNotes(BaseSchema):
    """Question-shaped notes about timing, duration, and renewal."""

    when_it_takes_effect_and_how_long_it_runs: DomainNote = Field(
        default_factory=DomainNote
    )
    how_renewal_or_extension_works: DomainNote = Field(default_factory=DomainNote)


class EconomicsNotes(BaseSchema):
    """Question-shaped notes about pricing, caps, and payment mechanics."""

    how_pricing_works: DomainNote = Field(default_factory=DomainNote)
    what_total_fee_or_cap_language_is_explicit: DomainNote = Field(
        default_factory=DomainNote
    )
    how_payment_is_described: DomainNote = Field(default_factory=DomainNote)


class ControlsNotes(BaseSchema):
    """Question-shaped notes about termination, risk, and compliance controls."""

    how_termination_or_exit_works: DomainNote = Field(default_factory=DomainNote)
    what_insurance_or_risk_requirements_apply: DomainNote = Field(
        default_factory=DomainNote
    )
    what_performance_or_compliance_obligations_matter: DomainNote = Field(
        default_factory=DomainNote
    )


class QualityNotes(BaseSchema):
    """Question-shaped notes about ambiguity, incompleteness, and caveats."""

    important_caveats_or_ambiguities: DomainNote = Field(default_factory=DomainNote)


class GoverningDomainNotesModelOutput(BaseSchema):
    """Model-facing governing note body without deterministic envelope fields."""

    identity: IdentityNotes = Field(default_factory=IdentityNotes)
    parties: PartiesNotes = Field(default_factory=PartiesNotes)
    subject: SubjectNotes = Field(default_factory=SubjectNotes)
    term: TermNotes = Field(default_factory=TermNotes)
    economics: EconomicsNotes = Field(default_factory=EconomicsNotes)
    controls: ControlsNotes = Field(default_factory=ControlsNotes)
    quality: QualityNotes = Field(default_factory=QualityNotes)


class GoverningDomainNotes(GoverningDomainNotesModelOutput):
    """Persisted governing contract-map artifact with deterministic envelope fields."""

    doc_id: str
    source_filename: str
    status: StageStatus = Field(default_factory=StageStatus)


@lru_cache(maxsize=32)
def governing_domain_notes_subset_model(
    domains: tuple[str, ...],
) -> type[BaseSchema]:
    """Return a model-facing governing-domain-notes schema for one domain subset."""
    field_map = {
        "identity": (IdentityNotes, Field(default_factory=IdentityNotes)),
        "parties": (PartiesNotes, Field(default_factory=PartiesNotes)),
        "subject": (SubjectNotes, Field(default_factory=SubjectNotes)),
        "term": (TermNotes, Field(default_factory=TermNotes)),
        "economics": (EconomicsNotes, Field(default_factory=EconomicsNotes)),
        "controls": (ControlsNotes, Field(default_factory=ControlsNotes)),
        "quality": (QualityNotes, Field(default_factory=QualityNotes)),
    }
    invalid = sorted(set(domains) - set(field_map))
    if invalid:
        raise ValueError(f"Unsupported governing-domain-notes subset: {invalid}")
    if not domains:
        raise ValueError("At least one governing-domain-notes domain is required.")
    model_fields = {domain: field_map[domain] for domain in domains}
    return create_model(  # type: ignore[return-value]
        "GoverningDomainNotesSubset_" + "_".join(domains),
        __base__=BaseSchema,
        **model_fields,
    )


class PageNoteModelOutput(BaseSchema):
    """Model-facing semantic page-note body without runtime-known envelope fields."""

    page_role: PageRole | None = None
    summary: str | None = None
    key_terms: list[str] = Field(default_factory=list)
    relevance_tags: list[PageRelevanceTag] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @staticmethod
    def _clean_text_list(values: object) -> list[str]:
        """Normalize simple string lists and drop empty members."""
        if not isinstance(values, list):
            return []
        cleaned: list[str] = []
        for item in values:
            if not isinstance(item, str):
                continue
            value = " ".join(item.split()).strip()
            if value:
                cleaned.append(value)
        return cleaned

    @staticmethod
    def _looks_like_ocr_gibberish(value: str) -> bool:
        """Return True when a key-term candidate is likely just OCR garbage."""
        compact = re.sub(r"\s+", "", value)
        if len(compact) < 6:
            return False
        if not re.search(r"[A-Za-z]", compact):
            return False
        letters = re.sub(r"[^A-Za-z]", "", compact)
        if not letters:
            return False
        vowels = sum(1 for ch in letters.lower() if ch in "aeiou")
        vowel_ratio = vowels / len(letters)
        has_long_upper_run = bool(re.search(r"[A-Z0-9]{8,}", compact))
        has_ocr_noise = bool(re.search(r"[0-9]{2,}", compact)) or any(ch in compact for ch in "_/\\")
        return (len(letters) >= 8 and vowel_ratio < 0.2 and has_long_upper_run) or (
            len(letters) >= 10 and vowel_ratio < 0.15 and has_ocr_noise
        )

    @field_validator("key_terms", mode="before")
    @classmethod
    def _normalize_key_terms(cls, value: object) -> list[str]:
        """Drop empty and obvious OCR-noise key terms."""
        cleaned = cls._clean_text_list(value)
        deduped: list[str] = []
        seen: set[str] = set()
        for item in cleaned:
            if cls._looks_like_ocr_gibberish(item):
                continue
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @field_validator("warnings", mode="before")
    @classmethod
    def _normalize_warnings(cls, value: object) -> list[str]:
        """Drop empty warnings and deduplicate repeated messages."""
        cleaned = cls._clean_text_list(value)
        deduped: list[str] = []
        seen: set[str] = set()
        for item in cleaned:
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped


class PageNote(PageNoteModelOutput):
    """Persisted page-note artifact with deterministic envelope fields."""

    doc_id: str
    source_filename: str
    page_number: int = Field(ge=1)
    status: StageStatus = Field(default_factory=StageStatus)


class PageNotesDocument(BaseSchema):
    """Assembled page-note artifact for one document."""

    doc_id: str
    source_filename: str
    page_notes: list[PageNote] = Field(default_factory=list)
    status: StageStatus = Field(default_factory=StageStatus)


class GoverningDomainNotesInput(BaseSchema):
    """Typed input contract for one governing domain-notes request."""

    doc_id: str
    source_filename: str
    model: str
    normalized_document_path: str


class GoverningDomainNotesTrialJudgment(BaseSchema):
    """Human QA template for sampled governing domain-notes outputs."""

    useful: bool | None = None
    identity_notes_useful: bool | None = None
    parties_notes_useful: bool | None = None
    subject_notes_useful: bool | None = None
    term_notes_useful: bool | None = None
    economics_notes_useful: bool | None = None
    controls_notes_useful: bool | None = None
    citations_useful: bool | None = None
    ready_for_pipeline: bool | None = None
    notes: str = ""


class PageNotesInput(BaseSchema):
    """Typed input contract for one page-notes request."""

    doc_id: str
    source_filename: str
    model: str
    normalized_document_path: str
    page_number: int = Field(ge=1)
    page_text: str
    page_representation: str | None = None
    page_quality_flags: list[str] = Field(default_factory=list)


class PageNoteTrialJudgment(BaseSchema):
    """Human QA template for sampled page-note outputs."""

    useful: bool | None = None
    correct_page_role: bool | None = None
    summary_useful: bool | None = None
    key_terms_useful: bool | None = None
    relevance_tags_useful: bool | None = None
    ready_for_pipeline: bool | None = None
    notes: str = ""


class ChangeKeyClause(BaseSchema):
    """One cited change clause that should help retrieval and later focused extraction."""

    label: str
    summary: str
    citations: list[Citation] = Field(default_factory=list)


class ChangeTargetArtifactNote(DomainNote):
    """What prior artifact this change appears to affect."""


class ChangeDomainNote(DomainNote):
    """A change-domain note with lightweight dimension tags."""

    dimensions: list[ChangeDimension] = Field(default_factory=list)


class ChangeResultingStateNote(DomainNote):
    """What post-change state is explicitly established, if any."""


class ChangeQuality(BaseSchema):
    """Quality metadata and caveats for change notes."""

    extraction_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class ChangeExtraction(BaseSchema):
    """Lightweight, retrieval-oriented change notes by domain."""

    doc_id: str
    source_filename: str
    target_artifact: ChangeTargetArtifactNote = Field(default_factory=ChangeTargetArtifactNote)
    change: ChangeDomainNote = Field(default_factory=ChangeDomainNote)
    resulting_state: ChangeResultingStateNote = Field(default_factory=ChangeResultingStateNote)
    key_clauses: list[ChangeKeyClause] = Field(default_factory=list)
    quality: ChangeQuality = Field(default_factory=ChangeQuality)
    citations: list[Citation] = Field(default_factory=list)
    status: StageStatus = Field(default_factory=StageStatus)

    @property
    def extraction_confidence(self) -> float | None:
        return self.quality.extraction_confidence

    @property
    def warnings(self) -> list[str]:
        return self.quality.warnings


class ChangeExtractionModelOutput(BaseSchema):
    """Model-facing change extraction body without request-known envelope fields."""

    target_artifact: ChangeTargetArtifactNote = Field(default_factory=ChangeTargetArtifactNote)
    change: ChangeDomainNote = Field(default_factory=ChangeDomainNote)
    resulting_state: ChangeResultingStateNote = Field(default_factory=ChangeResultingStateNote)
    key_clauses: list[ChangeKeyClause] = Field(default_factory=list)
    quality: ChangeQuality = Field(default_factory=ChangeQuality)
    citations: list[Citation] = Field(default_factory=list)


class ChangeExtractionInput(BaseSchema):
    """Typed input contract for one change extraction request."""

    doc_id: str
    source_filename: str
    model: str
    normalized_document_path: str
    classified_change_kind: ChangeKind


class ChangeExtractionTrialJudgment(BaseSchema):
    """Human QA template for sampled change extraction outputs."""

    useful: bool | None = None
    correct_target_summary: bool | None = None
    correct_change_notes: bool | None = None
    correct_dimensions: bool | None = None
    key_clauses_useful: bool | None = None
    evidence_quality_ok: bool | None = None
    ready_for_pipeline: bool | None = None
    notes: str = ""


class ExtractedField(BaseSchema):
    name: str
    value_type: FieldValueType
    value: str | bool | int | float | dict[str, str] | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    citations: list[Citation] = Field(default_factory=list)
    notes: str | None = None


class LifecycleEvent(BaseSchema):
    event_type: LifecycleEventType
    event_date: date | None = None
    summary: str
    citations: list[Citation] = Field(default_factory=list)


class CommercialTerms(BaseSchema):
    effective_date: date | None = None
    expiration_date: date | None = None
    renewal_term: str | None = None
    auto_renewal_flag: bool | None = None
    price_change_flag: bool | None = None
    price_change_summary: str | None = None
    modification_number: str | None = None
    governing_jurisdiction: str | None = None


class DocumentExtraction(BaseSchema):
    doc_id: str
    vendor_name: str | None = None
    contract_id: str | None = None
    parent_contract_id: str | None = None
    service_category: str | None = None
    term_summary: str | None = None
    termination_summary: str | None = None
    commercial_terms: CommercialTerms = Field(default_factory=CommercialTerms)
    extracted_fields: list[ExtractedField] = Field(default_factory=list)
    lifecycle_events: list[LifecycleEvent] = Field(default_factory=list)
    status: StageStatus = Field(default_factory=StageStatus)


def completed_governing_domain_notes_status() -> StageStatus:
    """Return a completed status block for validated governing-domain-notes outputs."""
    return StageStatus(status=ProcessingStatus.COMPLETED)


def completed_change_extraction_status() -> StageStatus:
    """Return a completed status block for validated change extraction outputs."""
    return StageStatus(status=ProcessingStatus.COMPLETED)
