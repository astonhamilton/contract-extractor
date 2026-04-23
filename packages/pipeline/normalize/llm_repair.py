from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from packages.llm.transforms.repair_normalization.config import RepairNormalizationConfig
from packages.llm.transforms.repair_normalization.task import build_repair_input, run_repair_normalization
from packages.pipeline.normalize.llm_selection import (
    is_repair_candidate,
    recompute_manifest_llm_flags,
)
from packages.pipeline.normalize.pdf_pages import (
    iter_manifest_paths,
    load_manifest,
    preferred_page_image_path,
    repo_relative_path,
    write_manifest,
)
from packages.schemas import DocumentManifest, PageArtifact


LOGGER = logging.getLogger(__name__)

PAGE_LLM_FLAGS = {
    "llm_repair_generated",
}

DOC_LLM_FLAGS = {
    "has_llm_repair_pages",
}


def repair_output_path(doc_dir: Path, page_number: int) -> Path:
    """Return the canonical repair-markdown output path for one page."""
    return doc_dir / "pages" / f"{page_number:04d}.repair.md"


def reset_page_llm_fields(page: PageArtifact) -> PageArtifact:
    """Return a page artifact with LLM-repair-only fields cleared for reruns."""
    base_flags = [flag for flag in page.quality_flags if flag not in PAGE_LLM_FLAGS]
    base_warnings = [warning for warning in page.warnings if not warning.startswith("LLM repair: ")]
    return page.model_copy(
        update={
            "quality_flags": base_flags,
            "warnings": base_warnings,
        }
    )


def process_repair_page(
    *,
    repo_root: Path,
    manifest,
    page: PageArtifact,
    config: RepairNormalizationConfig,
    doc_dir: Path,
) -> PageArtifact:
    """Run repair normalization for one page and merge the result into the page artifact."""
    clean_page = reset_page_llm_fields(page)
    page_stem = f"{page.page_number:04d}"
    image_path = preferred_page_image_path(repo_root, clean_page)
    pdf_text_path = doc_dir / "pages" / f"{page_stem}.txt"
    ocr_text_path = doc_dir / "pages" / f"{page_stem}.ocr.txt"
    output_path = repair_output_path(doc_dir, page.page_number)

    request = build_repair_input(
        doc_id=manifest.doc_id,
        source_filename=manifest.source_filename,
        page_number=page.page_number,
        model=config.model,
        quality_flags=clean_page.quality_flags,
        image_path=image_path,
        pdf_text_path=pdf_text_path,
        ocr_text_path=ocr_text_path,
    )
    result = run_repair_normalization(request, config)
    result_text = result.output_markdown or result.output_text or ""
    output_path.write_text(result_text + ("\n" if result_text else ""), encoding="utf-8")

    merged_flags = list(dict.fromkeys(clean_page.quality_flags + ["llm_repair_generated"]))
    merged_warnings = list(dict.fromkeys(clean_page.warnings + [f"LLM repair: {config.model} | {config.prompt_version}"]))
    return clean_page.model_copy(
        update={
            "repair_markdown_path": repo_relative_path(output_path, repo_root),
            "quality_flags": merged_flags,
            "warnings": merged_warnings,
        }
    )


def roll_up_doc_llm_flags(pages: list[PageArtifact], base_flags: list[str]) -> list[str]:
    """Recompute document-level LLM repair flags after generation updates."""
    flags = [flag for flag in base_flags if flag not in DOC_LLM_FLAGS]

    if any("llm_repair_generated" in page.quality_flags for page in pages):
        flags.append("has_llm_repair_pages")

    return list(dict.fromkeys(flags))


def normalize_document_llm_repair(
    *,
    repo_root: Path,
    manifest_path: Path,
    config: RepairNormalizationConfig,
) -> tuple[DocumentManifest, int, int]:
    """Run repair normalization for one document and write manifest updates."""
    manifest = load_manifest(manifest_path)
    doc_dir = manifest_path.parent

    updated_pages: list[PageArtifact] = []
    processed = 0
    skipped = 0

    for page in manifest.pages:
        if not is_repair_candidate(page):
            updated_pages.append(page)
            skipped += 1
            continue
        LOGGER.info(
            "LLM repair | file=%s | page=%s",
            manifest.source_filename,
            page.page_number,
        )
        updated_pages.append(
            process_repair_page(
                repo_root=repo_root,
                manifest=manifest,
                page=page,
                config=config,
                doc_dir=doc_dir,
            )
        )
        processed += 1

    manifest.pages = updated_pages
    manifest.quality_flags = roll_up_doc_llm_flags(updated_pages, manifest.quality_flags)
    manifest = recompute_manifest_llm_flags(manifest)
    write_manifest(manifest_path, manifest)
    return manifest, processed, skipped


def iter_repair_candidate_manifest_paths(processed_contracts_dir: Path) -> list[Path]:
    """Return manifest paths for documents with at least one repair-candidate page."""
    manifest_paths: list[Path] = []
    for manifest_path in iter_manifest_paths(processed_contracts_dir):
        manifest = load_manifest(manifest_path)
        if any(is_repair_candidate(page) for page in manifest.pages):
            manifest_paths.append(manifest_path)
    return manifest_paths


def normalize_llm_repair_documents(
    *,
    repo_root: Path,
    processed_contracts_dir: Path,
    config: RepairNormalizationConfig,
) -> dict[str, object]:
    """Run canonical repair normalization for all currently selected pages."""
    manifest_paths = iter_repair_candidate_manifest_paths(processed_contracts_dir)
    LOGGER.info(
        "Starting canonical LLM repair normalization | candidate_documents=%s | model=%s",
        len(manifest_paths),
        config.model,
    )
    document_count = 0
    page_count = 0
    processed_manifests: list[DocumentManifest] = []
    for index, manifest_path in enumerate(manifest_paths, start=1):
        LOGGER.info("LLM repair processing [%s/%s] %s", index, len(manifest_paths), manifest_path.parent.name)
        manifest, processed, _ = normalize_document_llm_repair(
            repo_root=repo_root,
            manifest_path=manifest_path,
            config=config,
        )
        processed_manifests.append(manifest)
        if processed:
            document_count += 1
            page_count += processed
    LOGGER.info(
        "Canonical LLM repair normalization complete | documents=%s | pages=%s",
        document_count,
        page_count,
    )
    return {
        "candidate_documents": len(manifest_paths),
        "processed_documents": document_count,
        "processed_pages": page_count,
        "processed_manifests": processed_manifests,
    }


def build_llm_repair_report(
    *,
    config: RepairNormalizationConfig,
    summary: dict[str, object],
) -> dict[str, object]:
    """Build a compact report for the canonical repair-normalization run."""
    processed_manifests = summary.get("processed_manifests", [])
    manifest_list = [manifest for manifest in processed_manifests if isinstance(manifest, DocumentManifest)]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": config.model,
        "prompt_version": config.prompt_version,
        "candidate_documents": summary["candidate_documents"],
        "processed_documents": summary["processed_documents"],
        "processed_pages": summary["processed_pages"],
        "processed": [
            {
                "doc_id": manifest.doc_id,
                "source_filename": manifest.source_filename,
                "quality_flags": manifest.quality_flags,
                "generated_repair_pages": [
                    page.page_number
                    for page in manifest.pages
                    if "llm_repair_generated" in page.quality_flags
                ],
            }
            for manifest in manifest_list
        ],
    }


def write_llm_repair_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the canonical repair-normalization report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
