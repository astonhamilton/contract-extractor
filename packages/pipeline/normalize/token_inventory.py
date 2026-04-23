from __future__ import annotations

import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from packages.pipeline.normalize.pdf_pages import absolute_repo_path, iter_manifest_paths, load_manifest
from packages.schemas import ArtifactKind, DocumentManifest, PageArtifact


TOKEN_CHARS_PER_TOKEN = 4.0
NORMALIZED_DOCUMENT_ARTIFACT_TYPE = "normalized_document_xml"
BEST_AVAILABLE_PRIORITY = (
    "repair_markdown",
    "markdown",
    "vision_markdown",
    "ocr_text",
    "text",
)


def estimate_tokens_from_text(text: str) -> int:
    """Estimate tokens from text length using a simple chars-per-token heuristic."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / TOKEN_CHARS_PER_TOKEN))


def read_text_if_exists(path: Path | None) -> str | None:
    """Read text if the path exists and contains non-empty content."""
    if path is None or not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def page_artifact_texts(repo_root: Path, page: PageArtifact) -> dict[str, str]:
    """Load available normalized text forms for one page."""
    artifacts: dict[str, str] = {}
    candidates = {
        "text": page.text_path,
        "ocr_text": page.ocr_text_path,
        "markdown": page.markdown_path,
        "vision_markdown": page.vision_markdown_path,
        "repair_markdown": page.repair_markdown_path,
    }
    for artifact_type, raw_path in candidates.items():
        if not raw_path:
            continue
        text = read_text_if_exists(absolute_repo_path(repo_root, raw_path))
        if text:
            artifacts[artifact_type] = text
    return artifacts


def best_available_artifact_type(artifact_types: set[str]) -> str | None:
    """Pick the best available artifact type using the configured preference order."""
    for artifact_type in BEST_AVAILABLE_PRIORITY:
        if artifact_type in artifact_types:
            return artifact_type
    return None


def normalized_document_path(repo_root: Path, manifest: DocumentManifest) -> Path | None:
    """Return the canonical normalized document XML path when present on the manifest."""
    for artifact in manifest.derived_artifacts:
        if artifact.kind != ArtifactKind.XML:
            continue
        if artifact.path.endswith("/derived/normalized_document.xml") or artifact.path.endswith(
            "derived/normalized_document.xml"
        ):
            return absolute_repo_path(repo_root, artifact.path)
    return None


def document_token_record(repo_root: Path, manifest: DocumentManifest) -> dict[str, object]:
    """Build a per-document token inventory record."""
    page_records: list[dict[str, object]] = []
    by_type_tokens: Counter[str] = Counter()
    by_type_pages: Counter[str] = Counter()
    best_total_tokens = 0
    best_type_counter: Counter[str] = Counter()

    for page in manifest.pages:
        artifact_texts = page_artifact_texts(repo_root, page)
        artifact_tokens = {
            artifact_type: estimate_tokens_from_text(text)
            for artifact_type, text in artifact_texts.items()
        }
        for artifact_type, tokens in artifact_tokens.items():
            by_type_tokens[artifact_type] += tokens
            by_type_pages[artifact_type] += 1

        best_type = best_available_artifact_type(set(artifact_tokens))
        best_tokens = artifact_tokens.get(best_type, 0) if best_type else 0
        if best_type:
            best_total_tokens += best_tokens
            best_type_counter[best_type] += 1

        page_records.append(
            {
                "page_number": page.page_number,
                "artifact_tokens": artifact_tokens,
                "best_available_type": best_type,
                "best_available_tokens": best_tokens,
            }
        )

    normalized_document = normalized_document_path(repo_root, manifest)
    normalized_document_text = read_text_if_exists(normalized_document)
    if normalized_document_text:
        normalized_document_tokens = estimate_tokens_from_text(normalized_document_text)
        by_type_tokens[NORMALIZED_DOCUMENT_ARTIFACT_TYPE] += normalized_document_tokens
        best_total_tokens = normalized_document_tokens
        best_type_counter = Counter({NORMALIZED_DOCUMENT_ARTIFACT_TYPE: 1})

    return {
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "page_count": manifest.page_count,
        "tokens_by_artifact_type": dict(by_type_tokens),
        "pages_by_artifact_type": dict(by_type_pages),
        "best_available_total_tokens": best_total_tokens,
        "best_available_type_counts": dict(best_type_counter),
        "normalized_document_path": str(normalized_document) if normalized_document else None,
        "pages": page_records,
    }


def load_token_inventory_manifests(processed_contracts_dir: Path) -> list[DocumentManifest]:
    """Load all manifests for token inventory analysis."""
    return [load_manifest(path) for path in iter_manifest_paths(processed_contracts_dir)]


def build_token_inventory_report(repo_root: Path, manifests: list[DocumentManifest]) -> dict[str, object]:
    """Build a corpus-wide token inventory report over normalized artifacts."""
    document_records = [document_token_record(repo_root, manifest) for manifest in manifests]

    corpus_tokens_by_type: Counter[str] = Counter()
    corpus_pages_by_type: Counter[str] = Counter()
    corpus_best_total_tokens = 0
    corpus_best_type_counts: Counter[str] = Counter()

    for record in document_records:
        corpus_tokens_by_type.update(record["tokens_by_artifact_type"])
        corpus_pages_by_type.update(record["pages_by_artifact_type"])
        corpus_best_total_tokens += int(record["best_available_total_tokens"])
        corpus_best_type_counts.update(record["best_available_type_counts"])

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "token_estimation_method": {
            "kind": "chars_per_token",
            "chars_per_token": TOKEN_CHARS_PER_TOKEN,
        },
        "best_available_priority": list(BEST_AVAILABLE_PRIORITY),
        "documents_total": len(document_records),
        "corpus": {
            "tokens_by_artifact_type": dict(corpus_tokens_by_type),
            "pages_by_artifact_type": dict(corpus_pages_by_type),
            "best_available_total_tokens": corpus_best_total_tokens,
            "best_available_type_counts": dict(corpus_best_type_counts),
        },
        "documents": document_records,
    }


def write_token_inventory_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the token inventory report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
