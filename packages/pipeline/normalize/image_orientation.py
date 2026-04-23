from __future__ import annotations

import os
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytesseract
from PIL import Image
from pytesseract import Output

from packages.pipeline.normalize.ocr_pages import ensure_tesseract_available, mean_confidence
from packages.pipeline.normalize.pdf_pages import (
    absolute_repo_path,
    alpha_ratio,
    iter_manifest_paths,
    load_manifest,
    repo_relative_path,
    symbol_ratio,
    write_manifest,
)
from packages.schemas import DocumentManifest, PageArtifact


LOGGER = logging.getLogger(__name__)

ORIENTATION_ANGLES = (0, 90, 180, 270)
PAGE_ORIENTATION_FLAGS = {
    "image_orientation_validated",
    "image_orientation_rotated",
}
DOC_ORIENTATION_FLAGS = {
    "has_validated_page_images",
    "has_rotated_page_images",
}
OSD_ROTATE_RE = re.compile(r"Rotate:\s*(\d+)")
OSD_CONFIDENCE_RE = re.compile(r"Orientation confidence:\s*([0-9.]+)")


@dataclass(frozen=True)
class OrientationCandidate:
    """OCR-derived score for one tested clockwise page rotation."""

    rotate_clockwise_degrees: int
    score: float
    confidence: float | None
    token_count: int
    char_count: int
    alpha_ratio_value: float
    symbol_ratio_value: float


def default_orientation_worker_count() -> int:
    """Return a conservative default worker count for orientation validation."""
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count - 1, 4))


def orientation_output_path(doc_dir: Path, page_number: int) -> Path:
    """Return the canonical upright-image output path for one page."""
    return doc_dir / "pages" / f"{page_number:04d}.upright.png"


def rotate_image_clockwise(image: Image.Image, degrees: int) -> Image.Image:
    """Return a rotated image for one of the canonical right-angle turns."""
    normalized = degrees % 360
    if normalized not in ORIENTATION_ANGLES:
        raise ValueError(f"Unsupported rotation: {degrees}")
    if normalized == 0:
        return image.copy()
    return image.rotate(-normalized, expand=True)


def parse_osd_rotation(osd_text: str) -> tuple[int | None, float | None]:
    """Extract Tesseract OSD rotate degrees and confidence when present."""
    rotate_match = OSD_ROTATE_RE.search(osd_text)
    confidence_match = OSD_CONFIDENCE_RE.search(osd_text)
    rotate = int(rotate_match.group(1)) if rotate_match else None
    confidence = float(confidence_match.group(1)) if confidence_match else None
    return rotate, confidence


def meaningful_tokens(ocr_data: dict[str, list[str]]) -> list[str]:
    """Extract non-empty OCR tokens from a Tesseract OCR result."""
    return [(token or "").strip() for token in ocr_data.get("text", []) if (token or "").strip()]


def score_orientation_candidate(image: Image.Image, rotate_clockwise_degrees: int) -> OrientationCandidate:
    """Run lightweight OCR against one rotation and score readability."""
    rotated = rotate_image_clockwise(image, rotate_clockwise_degrees)
    try:
        ocr_data = pytesseract.image_to_data(rotated, output_type=Output.DICT)
    finally:
        rotated.close()

    tokens = meaningful_tokens(ocr_data)
    text = " ".join(tokens)
    confidence = mean_confidence(ocr_data)
    char_count = len(text)
    token_count = len(tokens)
    alpha = alpha_ratio(text) if text else 0.0
    symbol = symbol_ratio(text) if text else 1.0

    score = (confidence or 0.0)
    score += min(token_count, 40) * 1.5
    score += min(char_count, 400) / 40.0
    score += alpha * 35.0
    score -= symbol * 25.0
    if char_count == 0:
        score -= 40.0
    if token_count < 4:
        score -= 10.0

    return OrientationCandidate(
        rotate_clockwise_degrees=rotate_clockwise_degrees,
        score=round(score, 4),
        confidence=round(confidence, 4) if confidence is not None else None,
        token_count=token_count,
        char_count=char_count,
        alpha_ratio_value=round(alpha, 4),
        symbol_ratio_value=round(symbol, 4),
    )


def choose_orientation_by_ocr(image: Image.Image) -> tuple[OrientationCandidate, list[OrientationCandidate]]:
    """Evaluate all right-angle rotations and choose the best OCR-scoring orientation."""
    candidates = [score_orientation_candidate(image, angle) for angle in ORIENTATION_ANGLES]
    candidates.sort(key=lambda item: item.score, reverse=True)
    best = candidates[0]
    current = next(item for item in candidates if item.rotate_clockwise_degrees == 0)
    if best.rotate_clockwise_degrees != 0 and best.score < current.score + 5.0:
        return current, sorted(candidates, key=lambda item: item.rotate_clockwise_degrees)
    return best, sorted(candidates, key=lambda item: item.rotate_clockwise_degrees)


def detect_image_orientation(image_path: Path) -> dict[str, object]:
    """Detect the best clockwise rotation needed to make one page upright."""
    ensure_tesseract_available()
    with Image.open(image_path) as image:
        osd_rotate: int | None = None
        osd_confidence: float | None = None
        try:
            osd_text = pytesseract.image_to_osd(image)
            osd_rotate, osd_confidence = parse_osd_rotation(osd_text)
        except Exception:  # noqa: BLE001
            osd_rotate = None
            osd_confidence = None

        if osd_rotate in ORIENTATION_ANGLES and osd_confidence is not None and osd_confidence >= 12.0:
            rotate_clockwise_degrees = osd_rotate % 360
            method = "osd"
            candidates: list[OrientationCandidate] = []
        else:
            chosen, candidates = choose_orientation_by_ocr(image)
            rotate_clockwise_degrees = chosen.rotate_clockwise_degrees
            method = "ocr_score"

    return {
        "rotate_clockwise_degrees": rotate_clockwise_degrees,
        "method": method,
        "osd_confidence": osd_confidence,
        "candidates": [
            {
                "rotate_clockwise_degrees": candidate.rotate_clockwise_degrees,
                "score": candidate.score,
                "confidence": candidate.confidence,
                "token_count": candidate.token_count,
                "char_count": candidate.char_count,
                "alpha_ratio": candidate.alpha_ratio_value,
                "symbol_ratio": candidate.symbol_ratio_value,
            }
            for candidate in candidates
        ],
    }


def reset_page_orientation_fields(page: PageArtifact) -> PageArtifact:
    """Return a page artifact with orientation-stage metadata cleared for reruns."""
    base_flags = [flag for flag in page.quality_flags if flag not in PAGE_ORIENTATION_FLAGS]
    base_warnings = [
        warning for warning in page.warnings if not warning.startswith("Image orientation: ")
    ]
    return page.model_copy(
        update={
            "validated_image_path": None,
            "image_rotation_degrees": None,
            "image_orientation_method": None,
            "quality_flags": base_flags,
            "warnings": base_warnings,
        }
    )


def page_needs_orientation_validation(repo_root: Path, page: PageArtifact) -> bool:
    """Return whether a page image still needs orientation validation."""
    if not page_needs_orientation_validation_from_manifest(page):
        return False
    source_path = absolute_repo_path(repo_root, page.image_path or "")
    if not source_path.exists():
        return False
    if page.validated_image_path:
        validated_path = absolute_repo_path(repo_root, page.validated_image_path)
        return not validated_path.exists()
    return True


def page_needs_orientation_validation_from_manifest(page: PageArtifact) -> bool:
    """Return whether a page image appears orientation-pending from manifest fields alone."""
    if not page.image_path:
        return False
    if (
        page.validated_image_path
        and page.image_rotation_degrees is not None
        and page.image_orientation_method
    ):
        return False
    return True


def target_orientation_page_numbers(repo_root: Path, manifest: DocumentManifest) -> list[int]:
    """Return page numbers that should run through image-orientation validation."""
    return [
        page.page_number
        for page in manifest.pages
        if page_needs_orientation_validation(repo_root, page)
    ]


def write_upright_image(source_image_path: Path, output_path: Path, rotate_clockwise_degrees: int) -> None:
    """Write a rotated upright image artifact for one page."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_image_path) as image:
        rotated = rotate_image_clockwise(image, rotate_clockwise_degrees)
        try:
            rotated.save(output_path)
        finally:
            rotated.close()


def merge_page_orientation_results(
    *,
    page: PageArtifact,
    repo_root: Path,
    validated_image_path: Path,
    rotate_clockwise_degrees: int,
    method: str,
) -> PageArtifact:
    """Merge orientation-validation outputs back into a page artifact."""
    merged_flags = list(dict.fromkeys(page.quality_flags + ["image_orientation_validated"]))
    if rotate_clockwise_degrees:
        merged_flags.append("image_orientation_rotated")
    merged_warnings = list(
        dict.fromkeys(
            page.warnings
            + [f"Image orientation: {method} | rotate_clockwise_degrees={rotate_clockwise_degrees}"]
        )
    )
    return page.model_copy(
        update={
            "validated_image_path": repo_relative_path(validated_image_path, repo_root),
            "image_rotation_degrees": rotate_clockwise_degrees,
            "image_orientation_method": method,
            "quality_flags": merged_flags,
            "warnings": merged_warnings,
        }
    )


def process_orientation_page(
    *,
    repo_root: Path,
    page: PageArtifact,
    doc_dir: Path,
) -> tuple[PageArtifact, dict[str, object]]:
    """Validate orientation for one page image and merge results into the page artifact."""
    clean_page = reset_page_orientation_fields(page)
    source_image_path = absolute_repo_path(repo_root, str(page.image_path))
    decision = detect_image_orientation(source_image_path)
    rotate_clockwise_degrees = int(decision["rotate_clockwise_degrees"])
    method = str(decision["method"])

    if rotate_clockwise_degrees == 0:
        validated_image_path = source_image_path
    else:
        validated_image_path = orientation_output_path(doc_dir, page.page_number)
        write_upright_image(source_image_path, validated_image_path, rotate_clockwise_degrees)

    updated_page = merge_page_orientation_results(
        page=clean_page,
        repo_root=repo_root,
        validated_image_path=validated_image_path,
        rotate_clockwise_degrees=rotate_clockwise_degrees,
        method=method,
    )
    result = {
        "page_number": page.page_number,
        "rotate_clockwise_degrees": rotate_clockwise_degrees,
        "method": method,
        "source_image_path": str(source_image_path),
        "validated_image_path": str(validated_image_path),
        "rotated": rotate_clockwise_degrees != 0,
        "osd_confidence": decision["osd_confidence"],
        "candidates": decision["candidates"],
    }
    return updated_page, result


def build_orientation_task(
    *,
    repo_root: Path,
    manifest_path: Path,
    manifest: DocumentManifest,
    page: PageArtifact,
    output_dir: Path | None = None,
) -> dict[str, object]:
    """Build a serializable orientation-processing task for one page."""
    doc_dir = manifest_path.parent if output_dir is None else output_dir
    source_image_path = absolute_repo_path(repo_root, str(page.image_path))
    return {
        "manifest_path": str(manifest_path),
        "doc_id": manifest.doc_id,
        "source_filename": manifest.source_filename,
        "page_number": page.page_number,
        "source_image_path": str(source_image_path),
        "validated_output_path": str(orientation_output_path(doc_dir, page.page_number)),
    }


def run_orientation_task(task: dict[str, object]) -> dict[str, object]:
    """Run orientation detection for one page task and optionally write an upright image."""
    source_image_path = Path(str(task["source_image_path"]))
    validated_output_path = Path(str(task["validated_output_path"]))
    decision = detect_image_orientation(source_image_path)
    rotate_clockwise_degrees = int(decision["rotate_clockwise_degrees"])

    if rotate_clockwise_degrees != 0:
        write_upright_image(source_image_path, validated_output_path, rotate_clockwise_degrees)

    return {
        "manifest_path": str(task["manifest_path"]),
        "doc_id": str(task["doc_id"]),
        "source_filename": str(task["source_filename"]),
        "page_number": int(task["page_number"]),
        "source_image_path": str(source_image_path),
        "validated_image_path": str(validated_output_path if rotate_clockwise_degrees else source_image_path),
        "rotate_clockwise_degrees": rotate_clockwise_degrees,
        "method": str(decision["method"]),
        "rotated": rotate_clockwise_degrees != 0,
        "osd_confidence": decision["osd_confidence"],
        "candidates": decision["candidates"],
    }


def roll_up_doc_orientation_flags(pages: Iterable[PageArtifact], base_flags: Iterable[str]) -> list[str]:
    """Roll page orientation outcomes into document-level orientation flags."""
    page_list = list(pages)
    flags = [flag for flag in base_flags if flag not in DOC_ORIENTATION_FLAGS]
    if any(page.validated_image_path for page in page_list):
        flags.append("has_validated_page_images")
    if any("image_orientation_rotated" in page.quality_flags for page in page_list):
        flags.append("has_rotated_page_images")
    return list(dict.fromkeys(flags))


def normalize_document_image_orientation(
    *,
    repo_root: Path,
    manifest_path: Path,
) -> tuple[DocumentManifest, int, list[dict[str, object]]]:
    """Run canonical image-orientation validation for one document manifest."""
    manifest = load_manifest(manifest_path)
    doc_dir = manifest_path.parent
    updated_pages: list[PageArtifact] = []
    page_results: list[dict[str, object]] = []

    for page in manifest.pages:
        if page_needs_orientation_validation(repo_root, page):
            updated_page, page_result = process_orientation_page(
                repo_root=repo_root,
                page=page,
                doc_dir=doc_dir,
            )
            updated_pages.append(updated_page)
            page_results.append(page_result)
        else:
            updated_pages.append(page)

    manifest.pages = updated_pages
    manifest.quality_flags = roll_up_doc_orientation_flags(updated_pages, manifest.quality_flags)
    write_manifest(manifest_path, manifest)
    return manifest, len(page_results), page_results


def iter_orientation_candidate_manifest_paths(repo_root: Path, processed_contracts_dir: Path) -> list[Path]:
    """Return manifest paths that currently contain at least one orientation candidate page."""
    manifest_paths: list[Path] = []
    for manifest_path in iter_manifest_paths(processed_contracts_dir):
        manifest = load_manifest(manifest_path)
        if any(page_needs_orientation_validation(repo_root, page) for page in manifest.pages):
            manifest_paths.append(manifest_path)
    return manifest_paths


def normalize_image_orientation_documents(
    *,
    repo_root: Path,
    processed_contracts_dir: Path,
    workers: int | None = None,
) -> dict[str, object]:
    """Run canonical image-orientation validation for all selected pages."""
    ensure_tesseract_available()
    manifest_paths = iter_orientation_candidate_manifest_paths(repo_root, processed_contracts_dir)
    worker_count = workers if workers is not None else 1
    LOGGER.info(
        "Starting image orientation validation | candidate_documents=%s | workers=%s",
        len(manifest_paths),
        worker_count,
    )
    tasks: list[dict[str, object]] = []
    manifests_by_path: dict[str, DocumentManifest] = {}
    for manifest_path in manifest_paths:
        manifest = load_manifest(manifest_path)
        manifests_by_path[str(manifest_path)] = manifest
        for page in manifest.pages:
            if page_needs_orientation_validation(repo_root, page):
                tasks.append(
                    build_orientation_task(
                        repo_root=repo_root,
                        manifest_path=manifest_path,
                        manifest=manifest,
                        page=page,
                    )
                )

    task_results: dict[tuple[str, int], dict[str, object]] = {}
    if worker_count > 1:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(run_orientation_task, task): task
                for task in tasks
            }
            for index, future in enumerate(as_completed(future_map), start=1):
                result = future.result()
                task_results[(str(result["manifest_path"]), int(result["page_number"]))] = result
                LOGGER.info(
                    "Image orientation progress [%s/%s] %s page %s | rotate=%s | method=%s",
                    index,
                    len(tasks),
                    result["doc_id"],
                    result["page_number"],
                    result["rotate_clockwise_degrees"],
                    result["method"],
                )
    else:
        for index, task in enumerate(tasks, start=1):
            result = run_orientation_task(task)
            task_results[(str(result["manifest_path"]), int(result["page_number"]))] = result
            LOGGER.info(
                "Image orientation progress [%s/%s] %s page %s | rotate=%s | method=%s",
                index,
                len(tasks),
                result["doc_id"],
                result["page_number"],
                result["rotate_clockwise_degrees"],
                result["method"],
            )

    processed_manifests: list[DocumentManifest] = []
    processed_page_results: list[dict[str, object]] = []
    processed_documents = 0
    processed_pages = 0
    rotated_pages = 0

    for manifest_path in manifest_paths:
        manifest = manifests_by_path[str(manifest_path)]
        updated_pages: list[PageArtifact] = []
        page_results: list[dict[str, object]] = []
        for page in manifest.pages:
            result = task_results.get((str(manifest_path), page.page_number))
            if result is None:
                updated_pages.append(page)
                continue
            clean_page = reset_page_orientation_fields(page)
            updated_pages.append(
                merge_page_orientation_results(
                    page=clean_page,
                    repo_root=repo_root,
                    validated_image_path=Path(str(result["validated_image_path"])),
                    rotate_clockwise_degrees=int(result["rotate_clockwise_degrees"]),
                    method=str(result["method"]),
                )
            )
            page_results.append(result)

        manifest.pages = updated_pages
        manifest.quality_flags = roll_up_doc_orientation_flags(updated_pages, manifest.quality_flags)
        write_manifest(manifest_path, manifest)
        processed_manifests.append(manifest)
        if page_results:
            processed_documents += 1
            processed_pages += len(page_results)
            rotated_pages += sum(1 for result in page_results if bool(result["rotated"]))
            processed_page_results.extend(
                [
                    {
                        "doc_id": manifest.doc_id,
                        "source_filename": manifest.source_filename,
                        **result,
                    }
                    for result in page_results
                ]
            )

    return {
        "candidate_documents": len(manifest_paths),
        "workers": worker_count,
        "processed_documents": processed_documents,
        "processed_pages": processed_pages,
        "rotated_pages": rotated_pages,
        "processed_manifests": processed_manifests,
        "processed_page_results": processed_page_results,
    }


def build_image_orientation_report(summary: dict[str, object]) -> dict[str, object]:
    """Build a compact report for the canonical image-orientation run."""
    results = list(summary.get("processed_page_results", []))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "candidate_documents": summary["candidate_documents"],
        "workers": summary["workers"],
        "processed_documents": summary["processed_documents"],
        "processed_pages": summary["processed_pages"],
        "rotated_pages": summary["rotated_pages"],
        "unchanged_pages": summary["processed_pages"] - summary["rotated_pages"],
        "pages": results,
    }


def write_image_orientation_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the canonical image-orientation report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
