from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import fitz

from packages.pipeline.normalize.pdf_pages import absolute_repo_path, iter_manifest_paths, load_manifest, repo_relative_path
from packages.schemas import DocumentManifest, ProcessingStatus


LOGGER = logging.getLogger(__name__)


def failed_manifests(processed_contracts_dir: Path) -> list[tuple[Path, DocumentManifest]]:
    """Return manifest paths and payloads for currently failed documents."""
    items: list[tuple[Path, DocumentManifest]] = []
    for manifest_path in iter_manifest_paths(processed_contracts_dir):
        manifest = load_manifest(manifest_path)
        if manifest.processing_status.status == ProcessingStatus.FAILED:
            items.append((manifest_path, manifest))
    return items


def render_failed_pdf_preview(
    *,
    repo_root: Path,
    manifest_path: Path,
    manifest: DocumentManifest,
    output_dir: Path,
) -> dict[str, object]:
    """Attempt to render the first page of a failed PDF into sampled preview space."""
    source_pdf_path = absolute_repo_path(repo_root, manifest.source_pdf)
    doc_output_dir = output_dir / manifest.doc_id
    doc_output_dir.mkdir(parents=True, exist_ok=True)
    preview_path = doc_output_dir / "0001.png"

    result = {
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "source_pdf": manifest.source_pdf,
        "error": manifest.processing_status.error,
        "renderable": False,
        "preview_path": None,
        "page_count": None,
        "render_error": None,
    }

    try:
        document = fitz.open(source_pdf_path)
        try:
            result["page_count"] = document.page_count
            if document.page_count > 0:
                page = document.load_page(0)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                pixmap.save(preview_path)
                result["renderable"] = True
                result["preview_path"] = repo_relative_path(preview_path, repo_root)
        finally:
            document.close()
    except Exception as error:
        result["render_error"] = str(error)

    return result


def build_failed_pdf_render_report(*, repo_root: Path, processed_contracts_dir: Path) -> dict[str, object]:
    """Build a report showing which failed PDFs can still be rendered to images."""
    output_dir = repo_root / "data" / "sampled" / "failed_render_preview"
    items = failed_manifests(processed_contracts_dir)
    LOGGER.info("Checking renderability for %s failed PDFs", len(items))

    results: list[dict[str, object]] = []
    for index, (manifest_path, manifest) in enumerate(items, start=1):
        LOGGER.info("Failed render check [%s/%s] %s", index, len(items), manifest_path.parent.name)
        results.append(
            render_failed_pdf_preview(
                repo_root=repo_root,
                manifest_path=manifest_path,
                manifest=manifest,
                output_dir=output_dir,
            )
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "preview_dir": repo_relative_path(output_dir, repo_root),
        "failed_document_count": len(results),
        "renderable_count": sum(1 for item in results if item["renderable"]),
        "results": results,
    }


def write_failed_pdf_render_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the failed-PDF renderability report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
