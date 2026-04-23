from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path

from packages.pipeline.normalize.assemble_normalized_document import (
    BEST_AVAILABLE_PRIORITY,
    best_available_page_representation,
    read_page_content,
)
from packages.pipeline.assistant_readiness import load_manifests
from packages.schemas import (
    ChangeExtraction,
    DocumentClassification,
    DocumentManifest,
    GoverningDomainNotes,
    PageNotesDocument,
    ProcurementContext,
    StageStatus,
)
from packages.llm.transforms.document_classification.coerce import coerce_document_classification_payload


def load_canonical_manifests(
    repo_root: Path,
    *,
    doc_ids: Sequence[str] | None = None,
) -> list[DocumentManifest]:
    """Load canonical manifests, optionally filtered to a target doc-id set."""
    manifests = load_manifests(repo_root / "data" / "processed" / "contracts")
    if not doc_ids:
        return manifests
    doc_id_set = set(doc_ids)
    return [manifest for manifest in manifests if manifest.doc_id in doc_id_set]


def manifest_doc_ids(manifests: Sequence[DocumentManifest]) -> list[str]:
    """Return manifest doc ids in stable order."""
    return [manifest.doc_id for manifest in manifests]


def json_dumps(value: object) -> str:
    """Serialize a Python value for SQLite JSON-text storage."""
    return json.dumps(value, ensure_ascii=True)


def stage_status_columns(prefix: str, status: StageStatus) -> dict[str, str | None]:
    """Flatten a StageStatus into prefixed SQLite columns."""
    return {
        f"{prefix}_status": str(status.status),
        f"{prefix}_updated_at": status.updated_at.isoformat(),
        f"{prefix}_version": status.version,
        f"{prefix}_error": status.error,
        f"{prefix}_warnings_json": json_dumps(status.warnings),
    }


def delete_by_doc_ids(
    connection: sqlite3.Connection,
    *,
    table: str,
    doc_ids: Sequence[str],
    where_sql: str = "doc_id = ?",
) -> None:
    """Delete rows for a scoped set of doc ids."""
    if not doc_ids:
        return
    connection.executemany(
        f"DELETE FROM {table} WHERE {where_sql}",
        [(doc_id,) for doc_id in doc_ids],
    )


def load_json_payload(repo_root: Path, repo_relative_path: str | None) -> dict[str, object] | None:
    """Load a canonical JSON payload from a repo-relative path when present."""
    if not repo_relative_path:
        return None
    path = repo_root / repo_relative_path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_procurement_context_model(
    repo_root: Path,
    manifest: DocumentManifest,
) -> ProcurementContext | None:
    """Load canonical procurement context for one manifest."""
    payload = load_json_payload(repo_root, manifest.procurement_context_path)
    if payload is None:
        return None
    return ProcurementContext.model_validate(payload)


def load_classification_model(
    repo_root: Path,
    manifest: DocumentManifest,
) -> DocumentClassification | None:
    """Load canonical classification for one manifest."""
    payload = load_json_payload(repo_root, manifest.classification_path)
    if payload is None:
        return None
    coerced = coerce_document_classification_payload(payload)
    return DocumentClassification.model_validate(coerced)


def load_governing_notes_model(
    repo_root: Path,
    manifest: DocumentManifest,
) -> GoverningDomainNotes | None:
    """Load canonical governing domain notes for one manifest."""
    payload = load_json_payload(repo_root, manifest.governing_domain_notes_path)
    if payload is None:
        return None
    return GoverningDomainNotes.model_validate(payload)


def load_change_notes_model(
    repo_root: Path,
    manifest: DocumentManifest,
) -> ChangeExtraction | None:
    """Load canonical change extraction for one manifest."""
    payload = load_json_payload(repo_root, manifest.change_extraction_path)
    if payload is None:
        return None
    return ChangeExtraction.model_validate(payload)


def load_page_notes_model(
    repo_root: Path,
    manifest: DocumentManifest,
) -> PageNotesDocument | None:
    """Load canonical page notes for one manifest."""
    page_notes_json_path: str | None = None
    for artifact in manifest.derived_artifacts:
        if str(artifact.kind) == "json" and artifact.path.endswith("/derived/page_notes.json"):
            page_notes_json_path = artifact.path
            break
    if page_notes_json_path is None and manifest.page_notes_path:
        candidate = manifest.page_notes_path.replace("normalized_page_notes.xml", "page_notes.json")
        if candidate != manifest.page_notes_path:
            page_notes_json_path = candidate
    payload = load_json_payload(repo_root, page_notes_json_path)
    if payload is None:
        return None
    return PageNotesDocument.model_validate(payload)


def page_artifact_map(manifest: DocumentManifest) -> dict[int, object]:
    """Index manifest page artifacts by page number."""
    return {page.page_number: page for page in manifest.pages}


def page_variant_priority(representation: str) -> int:
    """Return the normalized priority rank for a page representation."""
    priority_map = {
        name: index + 1
        for index, (name, _field_name) in enumerate(BEST_AVAILABLE_PRIORITY)
    }
    return priority_map[representation]


def join_answers(pairs: Iterable[tuple[str, str | None]]) -> str | None:
    """Join non-empty answer strings into one compact domain answer."""
    parts = [f"{label}: {answer.strip()}" for label, answer in pairs if answer and answer.strip()]
    if not parts:
        return None
    return "\n".join(parts)


def best_page_content_record(
    repo_root: Path,
    manifest: DocumentManifest,
    *,
    page_number: int,
) -> dict[str, object] | None:
    """Return the best available page content record for one manifest page."""
    artifact = page_artifact_map(manifest).get(page_number)
    if artifact is None:
        return None
    representation, source_path = best_available_page_representation(artifact)
    content = read_page_content(repo_root, source_path)
    if content is None:
        return None
    return {
        "representation": representation,
        "priority": page_variant_priority(str(representation)),
        "source_path": source_path,
        "content": content,
        "artifact": artifact,
    }


def page_variant_records(
    repo_root: Path,
    manifest: DocumentManifest,
    *,
    page_number: int,
) -> list[dict[str, object]]:
    """Return all available normalized page variants for one manifest page."""
    artifact = page_artifact_map(manifest).get(page_number)
    if artifact is None:
        return []

    variants: list[dict[str, object]] = []
    for representation, field_name in BEST_AVAILABLE_PRIORITY:
        source_path = getattr(artifact, field_name)
        content = read_page_content(repo_root, source_path)
        if not source_path or content is None:
            continue
        variants.append(
            {
                "representation": representation,
                "priority": page_variant_priority(representation),
                "source_path": source_path,
                "content": content,
                "artifact": artifact,
            }
        )
    return variants
