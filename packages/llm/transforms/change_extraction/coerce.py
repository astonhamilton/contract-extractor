from __future__ import annotations

import re


DIMENSION_ALIASES = {
    "notice": "control",
    "governance": "control",
    "administrative": "control",
}


def _clean_text(value: object) -> str | None:
    """Normalize simple whitespace noise on prose fields."""
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def _coerce_domain_note(updated: dict[str, object], field_name: str) -> None:
    """Normalize one nested domain note object."""
    raw = updated.get(field_name)
    if not isinstance(raw, dict):
        updated[field_name] = {"answer": None, "citations": []}
        return

    updated[field_name] = {
        "answer": _clean_text(raw.get("answer") if "answer" in raw else raw.get("notes")),
        "citations": raw.get("citations") if isinstance(raw.get("citations"), list) else [],
    }


def _coerce_change_note(updated: dict[str, object]) -> None:
    """Normalize the nested change note, including dimensions."""
    raw = updated.get("change")
    if not isinstance(raw, dict):
        updated["change"] = {"answer": None, "dimensions": [], "citations": []}
        return

    seen: set[str] = set()
    dimensions: list[str] = []
    raw_dimensions = raw.get("dimensions")
    if isinstance(raw_dimensions, list):
        for item in raw_dimensions:
            cleaned = _clean_text(item)
            if not cleaned or cleaned in seen:
                continue
            cleaned = DIMENSION_ALIASES.get(cleaned, cleaned)
            seen.add(cleaned)
            dimensions.append(cleaned)

    updated["change"] = {
        "answer": _clean_text(raw.get("answer") if "answer" in raw else raw.get("notes")),
        "dimensions": dimensions,
        "citations": raw.get("citations") if isinstance(raw.get("citations"), list) else [],
    }


def _coerce_quality(updated: dict[str, object]) -> None:
    """Normalize quality metadata."""
    raw = updated.get("quality")
    if not isinstance(raw, dict):
        raw = {}

    warnings = raw.get("warnings")
    normalized_warnings = (
        [cleaned for item in warnings if (cleaned := _clean_text(item)) is not None]
        if isinstance(warnings, list)
        else []
    )
    updated["quality"] = {
        "warnings": normalized_warnings,
        "extraction_confidence": raw.get("extraction_confidence"),
    }


def _coerce_key_clauses(updated: dict[str, object]) -> None:
    """Normalize key clauses into a small, retrieval-friendly list."""
    raw = updated.get("key_clauses")
    if not isinstance(raw, list):
        updated["key_clauses"] = []
        return

    normalized: list[dict[str, object]] = []
    for item in raw[:5]:
        if not isinstance(item, dict):
            continue
        label = _clean_text(item.get("label"))
        summary = _clean_text(item.get("summary"))
        citations = item.get("citations")
        if not label or not summary:
            continue
        normalized.append(
            {
                "label": label,
                "summary": summary,
                "citations": citations if isinstance(citations, list) else [],
            }
        )
    updated["key_clauses"] = normalized


def _coerce_confidence(updated: dict[str, object]) -> None:
    """Cap confidence modestly when the record is sparse or warning-heavy."""
    quality = updated.get("quality")
    if not isinstance(quality, dict):
        return

    confidence = quality.get("extraction_confidence")
    if not isinstance(confidence, (int, float)):
        return

    capped = float(confidence)
    warnings = quality.get("warnings")
    if isinstance(warnings, list):
        if len(warnings) >= 1:
            capped = min(capped, 0.94)
        if len(warnings) >= 2:
            capped = min(capped, 0.90)

    target_artifact = updated.get("target_artifact")
    change = updated.get("change")
    if not isinstance(target_artifact, dict) or not _clean_text(target_artifact.get("answer")):
        capped = min(capped, 0.90)
    if not isinstance(change, dict) or not _clean_text(change.get("answer")):
        capped = min(capped, 0.88)

    quality["extraction_confidence"] = round(capped, 2)
    updated["quality"] = quality


def coerce_change_extraction_payload(payload: dict[str, object]) -> dict[str, object]:
    """Normalize common near-miss outputs for lightweight note-based change extraction."""
    updated = dict(payload)

    _coerce_domain_note(updated, "target_artifact")
    _coerce_change_note(updated)
    _coerce_domain_note(updated, "resulting_state")
    _coerce_quality(updated)

    citations = updated.get("citations")
    if not isinstance(citations, list):
        updated["citations"] = []

    _coerce_key_clauses(updated)
    _coerce_confidence(updated)
    return updated
