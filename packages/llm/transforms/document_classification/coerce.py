from __future__ import annotations

from collections.abc import Mapping

from packages.schemas import completed_classification_status


LEGACY_DOCUMENT_TYPE_TO_STAGE_ROLE = {
    "agreement": ("contracting", "operative"),
    "task_order_or_sow": ("contracting", "operative"),
    "renewal": ("active_change", "delta"),
    "amendment": ("active_change", "delta"),
    "quote_or_pricing_sheet": ("sourcing", "context"),
    "bid_or_proposal": ("sourcing", "context"),
    "disclosure_or_compliance": ("compliance", "context"),
    "exhibit_or_schedule": ("unclear", "context"),
    "other": ("unclear", "context"),
}

LEGACY_DOCUMENT_TYPE_TO_CHANGE = {
    "renewal": "renewal",
    "amendment": "amendment",
    "quote_or_pricing_sheet": "pricing_update",
}

LEGACY_LIFECYCLE_TO_STAGE_ROLE = {
    "base": ("contracting", "operative"),
    "modifies_prior": ("active_change", "delta"),
    "extends_term": ("active_change", "delta"),
    "updates_pricing": ("active_change", "delta"),
    "supporting_only": ("unclear", "context"),
    "unclear": ("unclear", "context"),
}

LEGACY_LIFECYCLE_TO_CHANGE = {
    "modifies_prior": "amendment",
    "extends_term": "renewal",
    "updates_pricing": "pricing_update",
}

ALLOWED_KEYS = {
    "doc_id",
    "source_filename",
    "procurement_stage",
    "primary_document_role",
    "change_kind",
    "confidence",
    "evidence_pages",
    "rationale",
    "warnings",
    "evidence",
    "status",
}


def normalize_legacy_fields(updated: dict[str, object]) -> None:
    """Map legacy classification fields into the current schema."""
    stage = updated.get("procurement_stage")
    role = updated.get("primary_document_role")

    if not isinstance(role, str):
        legacy_role = updated.get("document_role")
        if isinstance(legacy_role, str):
            updated["primary_document_role"] = legacy_role

    if not isinstance(stage, str) or not isinstance(updated.get("primary_document_role"), str):
        legacy_type = updated.get("document_type")
        if isinstance(legacy_type, str):
            mapped = LEGACY_DOCUMENT_TYPE_TO_STAGE_ROLE.get(legacy_type.strip().lower())
            if mapped is not None:
                updated["procurement_stage"] = mapped[0]
                updated["primary_document_role"] = mapped[1]

    if not isinstance(updated.get("procurement_stage"), str) or not isinstance(updated.get("primary_document_role"), str):
        lifecycle = updated.get("lifecycle_role")
        if isinstance(lifecycle, str):
            mapped = LEGACY_LIFECYCLE_TO_STAGE_ROLE.get(lifecycle.strip().lower())
            if mapped is not None:
                updated["procurement_stage"] = mapped[0]
                updated["primary_document_role"] = mapped[1]

    if not isinstance(updated.get("change_kind"), str):
        legacy_type = updated.get("document_type")
        if isinstance(legacy_type, str):
            mapped = LEGACY_DOCUMENT_TYPE_TO_CHANGE.get(legacy_type.strip().lower())
            if mapped is not None:
                updated["change_kind"] = mapped

    if not isinstance(updated.get("change_kind"), str):
        lifecycle = updated.get("lifecycle_role")
        if isinstance(lifecycle, str):
            mapped = LEGACY_LIFECYCLE_TO_CHANGE.get(lifecycle.strip().lower())
            if mapped is not None:
                updated["change_kind"] = mapped

    attached = updated.get("attached_document_types")
    if isinstance(attached, list) and attached:
        warnings = updated.setdefault("warnings", [])
        if isinstance(warnings, list) and "mixed_bundle" not in warnings:
            warnings.append("mixed_bundle")


def ensure_core_fields(updated: dict[str, object]) -> None:
    """Backfill the minimum stage/role fields if the model omitted them entirely."""
    if not isinstance(updated.get("procurement_stage"), str):
        updated["procurement_stage"] = "unclear"
    if not isinstance(updated.get("primary_document_role"), str):
        updated["primary_document_role"] = "context"


def enforce_change_kind_semantics(updated: dict[str, object]) -> None:
    """Keep change_kind only for active-change delta documents."""
    if (
        updated.get("procurement_stage") != "active_change"
        or updated.get("primary_document_role") != "delta"
    ):
        updated["change_kind"] = None
        return

    if not isinstance(updated.get("change_kind"), str):
        updated["change_kind"] = "amendment"


def coerce_evidence_pages(updated: dict[str, object]) -> None:
    """Normalize evidence_pages into a unique integer list and promote snippets when present."""
    evidence_pages = updated.get("evidence_pages")
    if not isinstance(evidence_pages, list):
        return

    page_numbers: list[int] = []
    promoted_evidence: list[dict[str, object]] = []
    for item in evidence_pages:
        if isinstance(item, int):
            page_numbers.append(item)
            continue
        if isinstance(item, Mapping):
            page_number = item.get("page_number")
            if isinstance(page_number, int):
                page_numbers.append(page_number)
                label = item.get("label")
                snippet = item.get("snippet")
                if isinstance(label, str) and label.strip():
                    promoted_evidence.append(
                        {
                            "label": label,
                            "snippet": snippet if isinstance(snippet, str) else "",
                            "page_number": page_number,
                        }
                    )

    updated["evidence_pages"] = sorted(set(page_numbers))

    if promoted_evidence:
        existing = updated.get("evidence")
        if isinstance(existing, list):
            updated["evidence"] = existing + promoted_evidence
        else:
            updated["evidence"] = promoted_evidence


def coerce_document_classification_payload(payload: dict[str, object]) -> dict[str, object]:
    """Coerce legacy or near-miss payloads into the current classification schema."""
    updated: dict[str, object] = dict(payload)
    normalize_legacy_fields(updated)
    ensure_core_fields(updated)
    enforce_change_kind_semantics(updated)
    coerce_evidence_pages(updated)

    status = updated.get("status")
    if not isinstance(status, Mapping):
        updated["status"] = completed_classification_status().model_dump()

    for key in list(updated.keys()):
        if key not in ALLOWED_KEYS:
            del updated[key]

    return updated
