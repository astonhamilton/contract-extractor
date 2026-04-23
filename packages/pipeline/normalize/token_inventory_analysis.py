from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def load_token_inventory_report(report_path: Path) -> dict[str, object]:
    """Load a token inventory report from disk."""
    return json.loads(report_path.read_text(encoding="utf-8"))


def top_documents_by_best_available_tokens(
    report: dict[str, object],
    *,
    limit: int = 10,
) -> list[dict[str, object]]:
    """Return the top documents by best-available token total."""
    documents = list(report.get("documents", []))
    ranked = sorted(
        documents,
        key=lambda doc: (
            -int(doc.get("best_available_total_tokens", 0)),
            str(doc.get("source_filename", "")),
        ),
    )
    return ranked[:limit]


def top_documents_by_artifact_type(
    report: dict[str, object],
    *,
    artifact_type: str,
    limit: int = 10,
) -> list[dict[str, object]]:
    """Return the top documents by token total for one artifact type."""
    documents = list(report.get("documents", []))
    ranked = sorted(
        documents,
        key=lambda doc: (
            -int(doc.get("tokens_by_artifact_type", {}).get(artifact_type, 0)),
            str(doc.get("source_filename", "")),
        ),
    )
    return [doc for doc in ranked if int(doc.get("tokens_by_artifact_type", {}).get(artifact_type, 0)) > 0][:limit]


def best_available_mix(report: dict[str, object]) -> dict[str, int]:
    """Return the corpus-wide page mix of best-available artifact types."""
    return dict(report.get("corpus", {}).get("best_available_type_counts", {}))


def build_token_inventory_analysis(report: dict[str, object], *, limit: int = 10) -> dict[str, object]:
    """Build a compact analysis view over the token inventory report."""
    corpus = report.get("corpus", {})
    top_best = top_documents_by_best_available_tokens(report, limit=limit)
    top_text = top_documents_by_artifact_type(report, artifact_type="text", limit=limit)
    top_ocr = top_documents_by_artifact_type(report, artifact_type="ocr_text", limit=limit)
    top_markdown = top_documents_by_artifact_type(report, artifact_type="markdown", limit=limit)
    top_repair = top_documents_by_artifact_type(report, artifact_type="repair_markdown", limit=limit)

    return {
        "generated_from": report.get("generated_at"),
        "documents_total": report.get("documents_total"),
        "best_available_total_tokens": corpus.get("best_available_total_tokens", 0),
        "best_available_type_counts": best_available_mix(report),
        "tokens_by_artifact_type": dict(corpus.get("tokens_by_artifact_type", {})),
        "top_documents_by_best_available_tokens": top_best,
        "top_documents_by_text_tokens": top_text,
        "top_documents_by_ocr_tokens": top_ocr,
        "top_documents_by_markdown_tokens": top_markdown,
        "top_documents_by_repair_tokens": top_repair,
    }
