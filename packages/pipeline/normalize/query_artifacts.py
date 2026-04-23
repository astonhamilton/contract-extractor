from __future__ import annotations

import json
import os
import random
from collections.abc import Callable
from pathlib import Path

from packages.pipeline.normalize.analyze_quality import load_all_manifests
from packages.pipeline.normalize.pdf_pages import absolute_repo_path, load_manifest
from packages.pipeline.normalize.llm_selection import (
    markdown_candidates,
    repair_candidates,
    skipped_repair_pages,
    vision_markdown_candidates,
)
from packages.schemas import DocumentManifest, PageArtifact, ProcessingStatus


SelectorFn = Callable[[list], list[dict[str, object]]]


def relative_symlink(link_path: Path, target_path: Path) -> None:
    """Create or replace a relative symlink."""
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    relative_target = Path(os.path.relpath(target_path, start=link_path.parent))
    link_path.symlink_to(relative_target)


def safe_relative_path(path: Path, root: Path) -> str:
    """Convert a path into a root-relative string for report serialization."""
    return str(path.relative_to(root))


def selector_registry() -> dict[str, SelectorFn]:
    """Return supported candidate selectors for flat artifact queries."""
    return {
        "markdown": markdown_candidates,
        "repair": repair_candidates,
        "vision_markdown": vision_markdown_candidates,
        "skipped_repair": skipped_repair_pages,
        "markdown_generated": markdown_generated_pages,
        "vision_markdown_generated": vision_markdown_generated_pages,
        "repaired": repaired_pages,
        "failed": failed_documents,
    }


def page_record(manifest: DocumentManifest, page: PageArtifact) -> dict[str, object]:
    """Create a compact page record for generated-output query exports."""
    return {
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "page_number": page.page_number,
        "extraction_method": page.extraction_method,
        "char_count": page.char_count,
        "ocr_char_count": page.ocr_char_count,
        "ocr_confidence": page.ocr_confidence,
        "quality_flags": page.quality_flags,
    }


def markdown_generated_pages(manifests: list[DocumentManifest]) -> list[dict[str, object]]:
    """Return pages with canonical markdown output already generated."""
    pages: list[dict[str, object]] = []
    for manifest in manifests:
        for page in manifest.pages:
            if page.markdown_path:
                pages.append(page_record(manifest, page))
    return pages


def repaired_pages(manifests: list[DocumentManifest]) -> list[dict[str, object]]:
    """Return pages with canonical repair markdown output already generated."""
    pages: list[dict[str, object]] = []
    for manifest in manifests:
        for page in manifest.pages:
            if page.repair_markdown_path:
                pages.append(page_record(manifest, page))
    return pages


def vision_markdown_generated_pages(manifests: list[DocumentManifest]) -> list[dict[str, object]]:
    """Return pages with canonical vision markdown output already generated."""
    pages: list[dict[str, object]] = []
    for manifest in manifests:
        for page in manifest.pages:
            if page.vision_markdown_path:
                pages.append(page_record(manifest, page))
    return pages


def failed_documents(manifests: list[DocumentManifest]) -> list[dict[str, object]]:
    """Return one record per failed document for flat export."""
    records: list[dict[str, object]] = []
    for manifest in manifests:
        if manifest.processing_status.status != ProcessingStatus.FAILED:
            continue
        records.append(
            {
                "doc_id": manifest.doc_id,
                "source_filename": manifest.source_filename,
                "page_number": 0,
                "extraction_method": None,
                "char_count": 0,
                "ocr_char_count": 0,
                "ocr_confidence": None,
                "quality_flags": manifest.quality_flags,
                "error": manifest.processing_status.error,
            }
        )
    return records


def sample_items(items: list[dict[str, object]], *, limit: int | None, seed: int) -> list[dict[str, object]]:
    """Optionally sample a deterministic subset of candidate items."""
    if limit is None or limit >= len(items):
        return list(items)
    rng = random.Random(seed)
    return rng.sample(items, limit)


def candidate_source_paths(repo_root: Path, candidate: dict[str, object]) -> dict[str, Path]:
    """Resolve candidate artifact paths from processed outputs."""
    doc_id = str(candidate["doc_id"])
    page_number = int(candidate["page_number"])
    doc_dir = repo_root / "data" / "processed" / "contracts" / doc_id
    page_stem = f"{page_number:04d}"
    manifest_path = doc_dir / "manifest.json"
    source_pdf_path = manifest_path
    if manifest_path.exists():
        manifest = load_manifest(manifest_path)
        source_pdf_path = absolute_repo_path(repo_root, manifest.source_pdf)
    return {
        "manifest": manifest_path,
        "pdf": source_pdf_path,
        "text": doc_dir / "pages" / f"{page_stem}.txt",
        "ocr_text": doc_dir / "pages" / f"{page_stem}.ocr.txt",
        "image": doc_dir / "pages" / f"{page_stem}.png",
        "markdown": doc_dir / "pages" / f"{page_stem}.md",
        "vision_markdown": doc_dir / "pages" / f"{page_stem}.vision.md",
        "repair_markdown": doc_dir / "pages" / f"{page_stem}.repair.md",
    }


def artifact_filename(candidate: dict[str, object], artifact_name: str, source_path: Path) -> str:
    """Build a flat, collision-safe output filename for a linked artifact."""
    return f"{candidate['doc_id']}__page_{int(candidate['page_number']):04d}__{artifact_name}{source_path.suffix}"


def write_flat_query_output(
    *,
    repo_root: Path,
    output_dir: Path,
    selector_name: str,
    candidates: list[dict[str, object]],
    artifact_names: list[str],
    seed: int,
    limit: int | None,
) -> dict[str, object]:
    """Write a flat symlink export plus report for queried artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []

    for candidate in candidates:
        source_paths = candidate_source_paths(repo_root, candidate)
        linked_artifacts: dict[str, str] = {}
        for artifact_name in artifact_names:
            source_path = source_paths[artifact_name]
            if not source_path.exists():
                continue
            link_path = output_dir / artifact_filename(candidate, artifact_name, source_path)
            relative_symlink(link_path, source_path)
            linked_artifacts[artifact_name] = safe_relative_path(link_path, repo_root)

        record = {
            **candidate,
            "linked_artifacts": linked_artifacts,
        }
        records.append(record)

    report = {
        "selector": selector_name,
        "artifact_names": artifact_names,
        "seed": seed,
        "limit": limit,
        "output_dir": safe_relative_path(output_dir, repo_root),
        "count": len(records),
        "items": records,
    }
    report_path = output_dir / "query_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def run_artifact_query(
    *,
    repo_root: Path,
    selector_name: str,
    artifact_names: list[str],
    output_dir: Path,
    limit: int | None = None,
    seed: int = 42,
) -> dict[str, object]:
    """Run a flat artifact query and write symlinks plus a report into the chosen folder."""
    selectors = selector_registry()
    if selector_name not in selectors:
        raise ValueError(f"Unsupported selector: {selector_name}")

    manifests = load_all_manifests(repo_root / "data" / "processed" / "contracts")
    candidates = selectors[selector_name](manifests)
    selected = sample_items(candidates, limit=limit, seed=seed)
    return write_flat_query_output(
        repo_root=repo_root,
        output_dir=output_dir,
        selector_name=selector_name,
        candidates=selected,
        artifact_names=artifact_names,
        seed=seed,
        limit=limit,
    )
