from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from packages.llm.transforms.document_classification.coerce import coerce_document_classification_payload
from packages.pipeline.normalize.pdf_pages import iter_manifest_paths, load_manifest
from packages.schemas import DocumentClassification, DocumentManifest, ProcessingStatus


def load_manifests(processed_contracts_dir: Path) -> list[DocumentManifest]:
    """Load all manifests for assistant-readiness auditing."""
    return [load_manifest(path) for path in iter_manifest_paths(processed_contracts_dir)]


def repo_path_exists(repo_root: Path, repo_relative_path: str | None) -> bool:
    """Return True when a repo-relative artifact path exists on disk."""
    if not repo_relative_path:
        return False
    return (repo_root / repo_relative_path).exists()


def normalized_document_exists(repo_root: Path, manifest: DocumentManifest) -> bool:
    """Return True when the canonical normalized document exists for a manifest."""
    path = repo_root / "data" / "processed" / "contracts" / manifest.doc_id / "derived" / "normalized_document.xml"
    return path.exists()


def load_classification(repo_root: Path, manifest: DocumentManifest) -> DocumentClassification | None:
    """Load canonical classification when both manifest pointer and file exist."""
    if not repo_path_exists(repo_root, manifest.classification_path):
        return None
    payload = json.loads((repo_root / manifest.classification_path).read_text(encoding="utf-8"))
    payload = coerce_document_classification_payload(payload)
    return DocumentClassification.model_validate(payload)


def manifest_readiness(repo_root: Path, manifest: DocumentManifest) -> dict[str, object]:
    """Derive assistant-readiness state and next action for one document."""
    normalized_ready = (
        manifest.processing_status.status == ProcessingStatus.COMPLETED
        and normalized_document_exists(repo_root, manifest)
    )
    procurement_ready = repo_path_exists(repo_root, manifest.procurement_context_path)
    classification = load_classification(repo_root, manifest)
    classification_ready = classification is not None

    requires_governing = bool(
        classification and classification.routes_to_governing_domain_notes
    )
    requires_change = bool(classification and classification.routes_to_change_extraction)
    governing_ready = repo_path_exists(repo_root, manifest.governing_domain_notes_path)
    change_ready = repo_path_exists(repo_root, manifest.change_extraction_path)

    blockers: list[str] = []
    if not normalized_ready:
        blockers.append("normalize_document")
    if normalized_ready and not procurement_ready:
        blockers.append("procurement_context")
    if normalized_ready and not classification_ready:
        blockers.append("classification")
    if classification_ready and requires_governing and not governing_ready:
        blockers.append("governing_domain_notes")
    if classification_ready and requires_change and not change_ready:
        blockers.append("change_extraction")

    ready_for_loader = not blockers

    if blockers:
        next_action = blockers[0]
        current_state = f"missing_{next_action}"
    else:
        next_action = "none"
        current_state = "ready_for_loader"

    return {
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "normalized_ready": normalized_ready,
        "procurement_context_ready": procurement_ready,
        "classification_ready": classification_ready,
        "requires_governing_domain_notes": requires_governing,
        "governing_domain_notes_ready": governing_ready if requires_governing else None,
        "requires_change_extraction": requires_change,
        "change_extraction_ready": change_ready if requires_change else None,
        "ready_for_loader": ready_for_loader,
        "current_state": current_state,
        "next_action": next_action,
        "blockers": blockers,
    }


def stage_summary(
    states: list[dict[str, object]],
    *,
    required_key: str,
    ready_key: str,
) -> dict[str, int]:
    """Summarize required/ready counts for one routed downstream stage."""
    required = sum(1 for state in states if state.get(required_key) is True)
    done = sum(1 for state in states if state.get(required_key) is True and state.get(ready_key) is True)
    return {
        "done": done,
        "total_required": required,
        "remaining": max(required - done, 0),
    }


def build_assistant_readiness_report(repo_root: Path, manifests: list[DocumentManifest]) -> dict[str, object]:
    """Build a corpus-wide readiness report for DB load / assistant backend work."""
    states = [manifest_readiness(repo_root, manifest) for manifest in manifests]
    state_counts = Counter(str(state["current_state"]) for state in states)
    next_action_counts = Counter(str(state["next_action"]) for state in states)

    normalized_done = sum(1 for state in states if state["normalized_ready"])
    procurement_done = sum(1 for state in states if state["procurement_context_ready"])
    classification_done = sum(1 for state in states if state["classification_ready"])
    loader_ready = sum(1 for state in states if state["ready_for_loader"])

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_documents": len(states),
        "state_counts": dict(state_counts),
        "next_action_counts": dict(next_action_counts),
        "stages": {
            "normalized_document": {
                "done": normalized_done,
                "total_required": len(states),
                "remaining": max(len(states) - normalized_done, 0),
            },
            "procurement_context": {
                "done": procurement_done,
                "total_required": normalized_done,
                "remaining": max(normalized_done - procurement_done, 0),
            },
            "classification": {
                "done": classification_done,
                "total_required": normalized_done,
                "remaining": max(normalized_done - classification_done, 0),
            },
            "governing_domain_notes": stage_summary(
                states,
                required_key="requires_governing_domain_notes",
                ready_key="governing_domain_notes_ready",
            ),
            "change_extraction": stage_summary(
                states,
                required_key="requires_change_extraction",
                ready_key="change_extraction_ready",
            ),
        },
        "loader_readiness": {
            "ready": loader_ready,
            "remaining": max(len(states) - loader_ready, 0),
        },
        "documents": states,
    }


def write_assistant_readiness_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the assistant-readiness report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
