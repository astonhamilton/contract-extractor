from __future__ import annotations

from collections.abc import Mapping


COOPERATIVE_SIGNALS = (
    "sourcewell",
    "cooperative purchasing",
    "national cooperative",
    "piggyback",
)


def tighten_non_procurement_fields(updated: dict[str, object]) -> None:
    """Clear procurement-only detail when the record is explicitly non-procurement."""
    if updated.get("is_procurement_doc") != "no":
        return

    for key in (
        "buyer",
        "seller",
        "procurement_subject_summary",
        "procurement_category",
    ):
        updated[key] = None


def tighten_cooperative_buyer(updated: dict[str, object]) -> None:
    """Do not use cooperative entities like Sourcewell as buyer by default."""
    buyer = updated.get("buyer")
    if not isinstance(buyer, str):
        return

    lowered_buyer = buyer.lower()
    if not any(token in lowered_buyer for token in COOPERATIVE_SIGNALS):
        return

    updated["buyer"] = None
    warnings = updated.setdefault("warnings", [])
    if isinstance(warnings, list):
        warning = "cooperative_vehicle_present_buyer_not_explicit"
        if warning not in warnings:
            warnings.append(warning)


def dedupe_warnings_and_evidence(updated: dict[str, object]) -> None:
    """Deduplicate warning strings and exact evidence rows."""
    warnings = updated.get("warnings")
    if isinstance(warnings, list):
        seen_warnings: set[str] = set()
        normalized_warnings: list[str] = []
        for item in warnings:
            if not isinstance(item, str) or item in seen_warnings:
                continue
            seen_warnings.add(item)
            normalized_warnings.append(item)
        updated["warnings"] = normalized_warnings

    evidence = updated.get("evidence")
    if isinstance(evidence, list):
        seen_evidence: set[tuple[str, str, int]] = set()
        normalized_evidence: list[object] = []
        for item in evidence:
            if not isinstance(item, Mapping):
                continue
            label = item.get("label")
            snippet = item.get("snippet")
            page_number = item.get("page_number")
            if not isinstance(label, str) or not isinstance(snippet, str) or not isinstance(page_number, int):
                continue
            key = (label, snippet, page_number)
            if key in seen_evidence:
                continue
            seen_evidence.add(key)
            normalized_evidence.append(dict(item))
        updated["evidence"] = normalized_evidence


def tighten_confidence(updated: dict[str, object]) -> None:
    """Cap confidence when core procurement fields remain weak."""
    confidence = updated.get("confidence")
    if not isinstance(confidence, (int, float)):
        return

    capped = float(confidence)
    is_procurement_doc = updated.get("is_procurement_doc")
    buyer = updated.get("buyer")
    seller = updated.get("seller")
    subject = updated.get("procurement_subject_summary")
    category = updated.get("procurement_category")
    warnings = updated.get("warnings")
    warning_count = len(warnings) if isinstance(warnings, list) else 0

    if is_procurement_doc == "unclear":
        capped = min(capped, 0.75)
    elif is_procurement_doc == "yes":
        if not isinstance(buyer, str) or not buyer.strip():
            capped = min(capped, 0.86)
        if not isinstance(seller, str) or not seller.strip():
            capped = min(capped, 0.88)
        if not isinstance(subject, str) or not subject.strip():
            capped = min(capped, 0.84)
        if category is None:
            capped = min(capped, 0.86)

    if warning_count >= 2:
        capped = min(capped, 0.88)
    if warning_count >= 4:
        capped = min(capped, 0.80)

    updated["confidence"] = round(capped, 4)


def coerce_procurement_context_payload(payload: dict[str, object]) -> dict[str, object]:
    """Apply small deterministic cleanups to procurement-context output."""
    updated = dict(payload)
    tighten_non_procurement_fields(updated)
    tighten_cooperative_buyer(updated)
    dedupe_warnings_and_evidence(updated)
    tighten_confidence(updated)
    return updated
