from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from packages.pipeline.normalize.llm_selection import (
    REPAIR_SKIP_FLAGS,
    TABLE_MARKDOWN_FLAGS,
    markdown_candidates,
    repair_candidates,
    skipped_repair_pages,
)
from packages.pipeline.normalize.pdf_pages import iter_manifest_paths, load_manifest
from packages.schemas import DocumentManifest, ExtractionMethod, PageArtifact, ProcessingStatus


LOW_QUALITY_PAGE_FLAGS = {
    "no_text_extracted",
    "low_text_density",
    "suspected_scanned_page",
    "suspected_image_only_page",
    "suspected_garbled_text",
    "high_symbol_ratio",
    "high_whitespace_noise",
    "ocr_low_text_density",
    "ocr_low_confidence",
    "ocr_suspected_garbled_text",
    "ocr_high_symbol_ratio",
    "ocr_high_whitespace_noise",
    "ocr_failed",
}

def load_all_manifests(processed_contracts_dir: Path) -> list[DocumentManifest]:
    """Load every document manifest under the processed contracts directory."""
    return [load_manifest(path) for path in iter_manifest_paths(processed_contracts_dir)]


def iter_pages(manifests: Iterable[DocumentManifest]) -> Iterable[tuple[DocumentManifest, PageArtifact]]:
    """Yield document/page pairs for all pages across all manifests."""
    for manifest in manifests:
        for page in manifest.pages:
            yield manifest, page


def page_has_any_flag(page: PageArtifact, target_flags: set[str]) -> bool:
    """Return whether a page contains any flag in the target set."""
    return bool(set(page.quality_flags) & target_flags)


def mechanism_confidence_bucket(page: PageArtifact) -> str:
    """Classify a page into a rough confidence bucket by current extraction path."""
    flags = set(page.quality_flags)

    if page.extraction_method == ExtractionMethod.OCR:
        ocr_low_quality_flags = {
            "ocr_failed",
            "ocr_low_text_density",
            "ocr_low_confidence",
            "ocr_suspected_garbled_text",
            "ocr_high_symbol_ratio",
            "ocr_high_whitespace_noise",
            "ocr_not_better_than_pdf_text",
        }

        if "ocr_failed" in flags:
            return "ocr_failed"

        if page.ocr_char_count == 0:
            return "ocr_failed"

        if (
            page.ocr_confidence is not None
            and page.ocr_confidence >= 80
            and not (flags & ocr_low_quality_flags)
        ):
            return "ocr_high_confidence"

        if (
            page.ocr_confidence is not None
            and page.ocr_confidence >= 50
            and "ocr_failed" not in flags
            and "ocr_suspected_garbled_text" not in flags
            and "ocr_not_better_than_pdf_text" not in flags
        ):
            return "ocr_medium_confidence"

        if flags & ocr_low_quality_flags:
            return "ocr_low_confidence"

        if page.ocr_char_count >= max(page.char_count, 80):
            return "ocr_medium_confidence"

        return "ocr_low_confidence"

    if page.extraction_method == ExtractionMethod.PDF_TEXT:
        if not (flags & LOW_QUALITY_PAGE_FLAGS):
            return "pdf_text_high_confidence"
        return "pdf_text_low_confidence"

    return "other_or_unknown"


def manual_review_documents(manifests: Iterable[DocumentManifest]) -> list[dict[str, object]]:
    """Return document-level manual review candidates."""
    return [
        {
            "doc_id": manifest.doc_id,
            "source_filename": manifest.source_filename,
            "status": manifest.processing_status.status,
            "error": manifest.processing_status.error,
            "quality_flags": manifest.quality_flags,
        }
        for manifest in manifests
        if "manual_review_recommended" in manifest.quality_flags or manifest.processing_status.status == ProcessingStatus.FAILED
    ]


def build_quality_report(manifests: list[DocumentManifest]) -> dict[str, object]:
    """Build a corpus-wide normalization quality report from all manifests."""
    pages = list(iter_pages(manifests))

    doc_status_counter = Counter(str(manifest.processing_status.status) for manifest in manifests)
    doc_flag_counter = Counter(flag for manifest in manifests for flag in manifest.quality_flags)
    page_flag_counter = Counter(flag for _, page in pages for flag in page.quality_flags)
    page_method_counter = Counter(str(page.extraction_method) for _, page in pages)
    confidence_counter = Counter(mechanism_confidence_bucket(page) for _, page in pages)

    markdown_candidate_pages = markdown_candidates(manifests)
    repair_candidate_pages = repair_candidates(manifests)
    skipped_repair_candidate_pages = skipped_repair_pages(manifests)
    review_docs = manual_review_documents(manifests)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "note": (
            "Current table/form detection is heuristic only. OCR does not yet perform explicit "
            "image-layout analysis beyond OCR-derived signals and table/form heuristics."
        ),
        "documents": {
            "total": len(manifests),
            "status_counts": dict(doc_status_counter),
            "quality_flag_counts": dict(doc_flag_counter),
        },
        "pages": {
            "total": len(pages),
            "extraction_method_counts": dict(page_method_counter),
            "quality_flag_counts": dict(page_flag_counter),
            "confidence_buckets": dict(confidence_counter),
        },
        "llm_candidates": {
            "markdown_pages": markdown_candidate_pages,
            "markdown_page_count": len(markdown_candidate_pages),
            "repair_pages": repair_candidate_pages,
            "repair_page_count": len(repair_candidate_pages),
            "skipped_repair_pages": skipped_repair_candidate_pages,
            "skipped_repair_page_count": len(skipped_repair_candidate_pages),
            "markdown_reason_counts": dict(
                Counter(
                    flag
                    for candidate in markdown_candidate_pages
                    for flag in candidate["quality_flags"]
                    if flag in TABLE_MARKDOWN_FLAGS
                    or flag
                    in {
                        "suspected_scanned_page",
                        "suspected_image_only_page",
                        "ocr_low_confidence",
                        "ocr_high_whitespace_noise",
                        "ocr_improved_over_pdf_text",
                    }
                )
            ),
            "repair_reason_counts": dict(
                Counter(
                    flag
                    for candidate in repair_candidate_pages
                    for flag in candidate["quality_flags"]
                    if flag
                    in {
                        "ocr_failed",
                        "ocr_possible_handwriting",
                        "ocr_low_confidence",
                        "ocr_not_better_than_pdf_text",
                        "ocr_suspected_garbled_text",
                        "no_text_extracted",
                        "suspected_garbled_text",
                    }
                )
            ),
            "skipped_repair_reason_counts": dict(
                Counter(
                    flag
                    for candidate in skipped_repair_candidate_pages
                    for flag in candidate["quality_flags"]
                    if flag in REPAIR_SKIP_FLAGS
                )
            ),
        },
        "manual_review": {
            "documents": review_docs,
            "document_count": len(review_docs),
        },
    }


def write_quality_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the quality report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
