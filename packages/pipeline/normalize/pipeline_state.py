from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from packages.pipeline.normalize.image_orientation import page_needs_orientation_validation_from_manifest
from packages.pipeline.normalize.llm_selection import (
    is_markdown_candidate,
    is_repair_candidate,
    is_vision_markdown_candidate,
)
from packages.pipeline.normalize.ocr_selection import target_page_numbers
from packages.pipeline.normalize.pdf_pages import iter_manifest_paths, load_manifest
from packages.schemas import DocumentManifest, ProcessingStatus


def load_pipeline_manifests(processed_contracts_dir: Path) -> list[DocumentManifest]:
    """Load all manifests for pipeline-state auditing."""
    return [load_manifest(path) for path in iter_manifest_paths(processed_contracts_dir)]


def manifest_pipeline_state(manifest: DocumentManifest) -> dict[str, object]:
    """Derive a doc-level pipeline state and next action from current manifest state."""
    if manifest.processing_status.status == ProcessingStatus.FAILED:
        return {
            "doc_id": manifest.doc_id,
            "source_filename": manifest.source_filename,
            "current_state": "failed",
            "next_action": "manual_review",
            "quality_flags": manifest.quality_flags,
            "error": manifest.processing_status.error,
        }

    if not manifest.pages:
        return {
            "doc_id": manifest.doc_id,
            "source_filename": manifest.source_filename,
            "current_state": "inventory_only",
            "next_action": "normalize_txt",
            "quality_flags": manifest.quality_flags,
            "error": None,
        }

    if any(page_needs_orientation_validation_from_manifest(page) for page in manifest.pages):
        return {
            "doc_id": manifest.doc_id,
            "source_filename": manifest.source_filename,
            "current_state": "needs_image_orientation",
            "next_action": "validate_image_orientation",
            "quality_flags": manifest.quality_flags,
            "error": None,
        }

    if target_page_numbers(manifest):
        return {
            "doc_id": manifest.doc_id,
            "source_filename": manifest.source_filename,
            "current_state": "needs_ocr",
            "next_action": "normalize_ocr",
            "quality_flags": manifest.quality_flags,
            "error": None,
        }

    if any(is_markdown_candidate(page) for page in manifest.pages):
        return {
            "doc_id": manifest.doc_id,
            "source_filename": manifest.source_filename,
            "current_state": "needs_llm_markdown",
            "next_action": "normalize_llm_markdown",
            "quality_flags": manifest.quality_flags,
            "error": None,
        }

    if any(is_vision_markdown_candidate(page) for page in manifest.pages):
        return {
            "doc_id": manifest.doc_id,
            "source_filename": manifest.source_filename,
            "current_state": "needs_vision_markdown",
            "next_action": "normalize_vision_markdown",
            "quality_flags": manifest.quality_flags,
            "error": None,
        }

    if any(is_repair_candidate(page) for page in manifest.pages):
        return {
            "doc_id": manifest.doc_id,
            "source_filename": manifest.source_filename,
            "current_state": "needs_llm_repair",
            "next_action": "normalize_llm_repair",
            "quality_flags": manifest.quality_flags,
            "error": None,
        }

    if "manual_review_recommended" in manifest.quality_flags:
        return {
            "doc_id": manifest.doc_id,
            "source_filename": manifest.source_filename,
            "current_state": "done_with_review_flag",
            "next_action": "none",
            "quality_flags": manifest.quality_flags,
            "error": None,
        }

    return {
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "current_state": "done",
        "next_action": "none",
        "quality_flags": manifest.quality_flags,
        "error": None,
    }


def build_pipeline_state_report(manifests: list[DocumentManifest]) -> dict[str, object]:
    """Build a corpus-wide pipeline state report from manifest state."""
    states = [manifest_pipeline_state(manifest) for manifest in manifests]
    counter = Counter(state["current_state"] for state in states)
    next_action_counter = Counter(state["next_action"] for state in states)
    failed_count = counter.get("failed", 0)
    not_run_count = counter.get("inventory_only", 0)

    text_done = sum(
        1
        for manifest in manifests
        if manifest.processing_status.status != ProcessingStatus.FAILED and bool(manifest.pages)
    )
    text_total_matched = len(manifests) - failed_count

    orientation_done = sum(1 for manifest in manifests if "has_validated_page_images" in manifest.quality_flags)
    orientation_total_matched = sum(
        1
        for manifest in manifests
        if "has_validated_page_images" in manifest.quality_flags
        or any(page_needs_orientation_validation_from_manifest(page) for page in manifest.pages)
    )

    ocr_done = sum(1 for manifest in manifests if "has_ocr_pages" in manifest.quality_flags)
    ocr_total_matched = sum(
        1
        for manifest in manifests
        if "has_ocr_pages" in manifest.quality_flags or any(target_page_numbers(manifest))
    )

    markdown_done = sum(1 for manifest in manifests if "has_llm_markdown_pages" in manifest.quality_flags)
    markdown_total_matched = sum(
        1
        for manifest in manifests
        if "has_llm_markdown_pages" in manifest.quality_flags
        or any(is_markdown_candidate(page) for page in manifest.pages)
    )

    vision_markdown_done = sum(1 for manifest in manifests if "has_llm_vision_markdown_pages" in manifest.quality_flags)
    vision_markdown_total_matched = sum(
        1
        for manifest in manifests
        if "has_llm_vision_markdown_pages" in manifest.quality_flags
        or any(is_vision_markdown_candidate(page) for page in manifest.pages)
    )

    repair_done = sum(1 for manifest in manifests if "has_llm_repair_pages" in manifest.quality_flags)
    repair_total_matched = sum(
        1
        for manifest in manifests
        if "has_llm_repair_pages" in manifest.quality_flags
        or any(is_repair_candidate(page) for page in manifest.pages)
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_documents": len(manifests),
        "state_counts": dict(counter),
        "next_action_counts": dict(next_action_counter),
        "stages": {
            "normalize_txt": {
                "done": text_done,
                "total_matched": text_total_matched,
                "remaining": max(text_total_matched - text_done, 0),
            },
            "validate_image_orientation": {
                "done": orientation_done,
                "total_matched": orientation_total_matched,
                "remaining": max(orientation_total_matched - orientation_done, 0),
            },
            "normalize_ocr": {
                "done": ocr_done,
                "total_matched": ocr_total_matched,
                "remaining": max(ocr_total_matched - ocr_done, 0),
            },
            "normalize_llm_markdown": {
                "done": markdown_done,
                "total_matched": markdown_total_matched,
                "remaining": max(markdown_total_matched - markdown_done, 0),
            },
            "normalize_vision_markdown": {
                "done": vision_markdown_done,
                "total_matched": vision_markdown_total_matched,
                "remaining": max(vision_markdown_total_matched - vision_markdown_done, 0),
            },
            "normalize_llm_repair": {
                "done": repair_done,
                "total_matched": repair_total_matched,
                "remaining": max(repair_total_matched - repair_done, 0),
            },
        },
        "no_stage": {
            "failed": failed_count,
            "not_run": not_run_count,
        },
        "documents": states,
    }


def write_pipeline_state_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the pipeline state report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
