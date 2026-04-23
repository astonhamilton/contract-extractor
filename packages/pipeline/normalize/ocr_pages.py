from __future__ import annotations

import json
import logging
import os
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import fitz
import pytesseract
from PIL import Image
from PIL import ImageStat
from pytesseract import Output

from packages.pipeline.normalize.pdf_pages import (
    absolute_repo_path,
    alpha_ratio,
    load_manifest,
    preferred_page_image_path,
    newline_ratio,
    repo_relative_path,
    symbol_ratio,
    write_manifest,
)
from packages.pipeline.normalize.llm_selection import recompute_manifest_llm_flags
from packages.pipeline.normalize.ocr_selection import target_page_numbers
from packages.schemas import DocumentManifest, ExtractionMethod, PageArtifact, ProcessingStatus


LOGGER = logging.getLogger(__name__)

PAGE_OCR_FLAGS = {
    "ocr_attempted",
    "ocr_succeeded",
    "ocr_failed",
    "ocr_low_text_density",
    "ocr_low_confidence",
    "ocr_high_symbol_ratio",
    "ocr_high_whitespace_noise",
    "ocr_suspected_garbled_text",
    "ocr_possible_table_or_form_content",
    "ocr_possible_handwriting",
    "ocr_improved_over_pdf_text",
    "ocr_not_better_than_pdf_text",
    "likely_blank_page",
    "likely_low_information_page",
    "skip_llm_repair",
    "llm_markdown_recommended",
    "llm_repair_recommended",
    "llm_normalization_recommended",
}

DOC_OCR_FLAGS = {
    "has_ocr_pages",
    "has_low_quality_ocr_pages",
    "ocr_improved_some_pages",
    "ocr_still_needs_review",
    "has_likely_blank_pages",
    "has_low_information_pages",
    "llm_markdown_recommended",
    "llm_repair_recommended",
    "llm_normalization_recommended",
}


def ensure_tesseract_available() -> None:
    """Ensure the Tesseract binary is available before running OCR."""
    if shutil.which("tesseract") is None:
        raise RuntimeError("Tesseract binary not found on PATH. Install tesseract to run OCR.")


def reset_page_ocr_fields(page: PageArtifact) -> PageArtifact:
    """Return a page artifact with OCR-derived fields cleared for a clean rerun."""
    base_flags = [flag for flag in page.quality_flags if flag not in PAGE_OCR_FLAGS]
    base_warnings = [warning for warning in page.warnings if not warning.startswith("OCR: ")]
    return page.model_copy(
        update={
            "ocr_text_path": None,
            "ocr_char_count": 0,
            "ocr_confidence": None,
            "quality_flags": base_flags,
            "warnings": base_warnings,
        }
    )
def rendered_image_output_path(doc_dir: Path, page_number: int) -> Path:
    """Return the canonical rendered image path for an OCR page."""
    return doc_dir / "pages" / f"{page_number:04d}.png"


def ocr_text_output_path(doc_dir: Path, page_number: int) -> Path:
    """Return the canonical OCR text path for an OCR page."""
    return doc_dir / "pages" / f"{page_number:04d}.ocr.txt"


def render_page_image(pdf_path: Path, page_number: int, image_path: Path) -> None:
    """Render one PDF page to a PNG image suitable for OCR."""
    document = fitz.open(pdf_path)
    try:
        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pixmap.save(image_path)
    finally:
        document.close()


def normalize_ocr_text(text: str) -> str:
    """Apply light deterministic cleanup to OCR text."""
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned.strip()


def mean_confidence(ocr_data: dict[str, list[str]]) -> float | None:
    """Compute mean OCR confidence over recognized words."""
    confidences: list[float] = []
    for raw_confidence, token in zip(ocr_data.get("conf", []), ocr_data.get("text", []), strict=False):
        token_text = (token or "").strip()
        if not token_text:
            continue
        try:
            confidence = float(raw_confidence)
        except ValueError:
            continue
        if confidence >= 0:
            confidences.append(confidence)
    if not confidences:
        return None
    return sum(confidences) / len(confidences)


def image_information_profile(image_path: Path) -> dict[str, float]:
    """Compute a few image statistics used for low-information page detection."""
    image = Image.open(image_path)
    try:
        grayscale = image.convert("L")
        stat = ImageStat.Stat(grayscale)
        mean_brightness = stat.mean[0]
        variance = stat.var[0]
        width, height = grayscale.size
        pixel_count = max(1, width * height)
        histogram = grayscale.histogram()
        near_white_pixels = sum(histogram[245:256])
        near_white_ratio = near_white_pixels / pixel_count
        near_black_pixels = sum(histogram[0:11])
        near_black_ratio = near_black_pixels / pixel_count
    finally:
        image.close()

    return {
        "mean_brightness": mean_brightness,
        "variance": variance,
        "near_white_ratio": near_white_ratio,
        "near_black_ratio": near_black_ratio,
    }


def is_likely_blank_image(image_path: Path) -> bool:
    """Heuristically detect whether a rendered page image is visually blank or near-blank white."""
    profile = image_information_profile(image_path)
    return (
        profile["mean_brightness"] >= 248
        and profile["variance"] <= 12
        and profile["near_white_ratio"] >= 0.985
    )


def is_likely_low_information_image(image_path: Path) -> bool:
    """Heuristically detect solid/near-solid pages that are not useful for LLM repair."""
    profile = image_information_profile(image_path)
    return (
        (profile["variance"] <= 12 and profile["near_white_ratio"] >= 0.985)
        or (
            profile["near_black_ratio"] >= 0.97
            and profile["mean_brightness"] <= 20
            and profile["variance"] <= 150
        )
    )


def numeric_token_ratio(ocr_data: dict[str, list[str]]) -> float:
    """Compute the ratio of mostly numeric OCR tokens."""
    tokens = [(token or "").strip() for token in ocr_data.get("text", [])]
    meaningful = [token for token in tokens if token]
    if not meaningful:
        return 0.0
    numeric = sum(1 for token in meaningful if sum(char.isdigit() for char in token) >= max(1, len(token) // 2))
    return numeric / len(meaningful)


def ocr_quality_signals(
    ocr_text: str,
    confidence: float | None,
    pdf_text_char_count: int,
    ocr_data: dict[str, list[str]],
    likely_blank_image: bool,
    likely_low_information_image: bool,
) -> tuple[list[str], list[str]]:
    """Derive OCR-specific quality flags and warnings."""
    flags = ["ocr_attempted"]
    warnings: list[str] = []

    char_count = len(ocr_text)
    if likely_low_information_image and char_count < 15:
        flags.extend(["likely_low_information_page", "skip_llm_repair"])
        warnings.append("Rendered page image appears low-information or nearly solid.")
    if likely_blank_image and char_count < 15:
        flags.extend(["likely_blank_page", "skip_llm_repair"])
        warnings.append("Rendered page image appears visually blank.")

    if char_count > 0:
        flags.append("ocr_succeeded")
    else:
        flags.append("ocr_failed")
        warnings.append("No text was recovered from this page.")
        if "likely_blank_page" not in flags and "likely_low_information_page" not in flags:
            flags.append("llm_repair_recommended")
        return list(dict.fromkeys(flags)), list(dict.fromkeys(warnings))

    if char_count < 40:
        flags.append("ocr_low_text_density")
        warnings.append("Very little text was recovered from this page.")

    if confidence is not None and confidence < 55:
        flags.append("ocr_low_confidence")
        warnings.append(f"Mean confidence is low ({confidence:.1f}).")

    if alpha_ratio(ocr_text) < 0.35 and char_count >= 40:
        flags.append("ocr_suspected_garbled_text")

    if symbol_ratio(ocr_text) > 0.35 and char_count >= 40:
        flags.append("ocr_high_symbol_ratio")

    if newline_ratio(ocr_text) > 0.12 and char_count >= 80:
        flags.append("ocr_high_whitespace_noise")

    if numeric_token_ratio(ocr_data) > 0.3:
        flags.append("ocr_possible_table_or_form_content")

    if confidence is not None and confidence < 45 and char_count < max(pdf_text_char_count, 80):
        flags.append("ocr_possible_handwriting")

    if char_count > pdf_text_char_count + 50:
        flags.append("ocr_improved_over_pdf_text")
    else:
        flags.append("ocr_not_better_than_pdf_text")

    if "ocr_possible_table_or_form_content" in flags:
        flags.append("llm_markdown_recommended")

    if any(
        flag in flags
        for flag in (
            "ocr_low_text_density",
            "ocr_low_confidence",
            "ocr_suspected_garbled_text",
            "ocr_possible_handwriting",
        )
    ):
        flags.append("llm_repair_recommended")

    return list(dict.fromkeys(flags)), list(dict.fromkeys(warnings))


def merge_page_ocr_results(
    page: PageArtifact,
    image_path: Path,
    ocr_text_path: Path,
    confidence: float | None,
    ocr_text: str,
    ocr_flags: list[str],
    ocr_warnings: list[str],
    repo_root: Path,
) -> PageArtifact:
    """Merge OCR outputs back into a page artifact."""
    merged_flags = list(dict.fromkeys(page.quality_flags + ocr_flags))
    merged_warnings = list(dict.fromkeys(page.warnings + [f"OCR: {warning}" for warning in ocr_warnings]))
    updated_extraction_method = ExtractionMethod.OCR if "ocr_improved_over_pdf_text" in ocr_flags else page.extraction_method
    return page.model_copy(
        update={
            "ocr_text_path": repo_relative_path(ocr_text_path, repo_root),
            "image_path": repo_relative_path(image_path, repo_root),
            "ocr_char_count": len(ocr_text),
            "ocr_confidence": confidence,
            "quality_flags": merged_flags,
            "warnings": merged_warnings,
            "extraction_method": updated_extraction_method,
        }
    )


def roll_up_doc_ocr_flags(pages: Iterable[PageArtifact], base_flags: Iterable[str]) -> list[str]:
    """Roll OCR page outcomes into document-level OCR flags."""
    page_list = list(pages)
    flags = [flag for flag in base_flags if flag not in DOC_OCR_FLAGS]

    if any("ocr_attempted" in page.quality_flags for page in page_list):
        flags.append("has_ocr_pages")
    if any(
        flag in page.quality_flags
        for page in page_list
        for flag in ("ocr_low_text_density", "ocr_low_confidence", "ocr_suspected_garbled_text")
    ):
        flags.append("has_low_quality_ocr_pages")
    if any("ocr_improved_over_pdf_text" in page.quality_flags for page in page_list):
        flags.append("ocr_improved_some_pages")
    if any("likely_blank_page" in page.quality_flags for page in page_list):
        flags.append("has_likely_blank_pages")
    if any("likely_low_information_page" in page.quality_flags for page in page_list):
        flags.append("has_low_information_pages")
    if any("llm_markdown_recommended" in page.quality_flags for page in page_list):
        flags.append("llm_markdown_recommended")
    if any("llm_repair_recommended" in page.quality_flags for page in page_list):
        flags.extend(["ocr_still_needs_review", "llm_repair_recommended"])

    return list(dict.fromkeys(flags))


def process_page_ocr(
    pdf_path: Path,
    doc_dir: Path,
    page: PageArtifact,
    repo_root: Path,
) -> PageArtifact:
    """Run OCR for a single flagged page and merge results back into the page artifact."""
    clean_page = reset_page_ocr_fields(page)
    source_image_path = rendered_image_output_path(doc_dir, clean_page.page_number)
    ocr_path = ocr_text_output_path(doc_dir, clean_page.page_number)

    if not source_image_path.exists():
        render_page_image(pdf_path, clean_page.page_number, source_image_path)
    input_image_path = preferred_page_image_path(repo_root, clean_page) or source_image_path
    likely_blank_image = is_likely_blank_image(input_image_path)
    likely_low_information_image = is_likely_low_information_image(input_image_path)
    image = Image.open(input_image_path)
    try:
        ocr_data = pytesseract.image_to_data(image, output_type=Output.DICT)
        ocr_text = normalize_ocr_text(pytesseract.image_to_string(image))
    finally:
        image.close()

    ocr_path.write_text(ocr_text + ("\n" if ocr_text else ""), encoding="utf-8")
    confidence = mean_confidence(ocr_data)
    ocr_flags, ocr_warnings = ocr_quality_signals(
        ocr_text=ocr_text,
        confidence=confidence,
        pdf_text_char_count=clean_page.char_count,
        ocr_data=ocr_data,
        likely_blank_image=likely_blank_image,
        likely_low_information_image=likely_low_information_image,
    )

    LOGGER.info(
        "OCR page %s | pdf_chars=%s | ocr_chars=%s | conf=%s | flags=%s",
        clean_page.page_number,
        clean_page.char_count,
        len(ocr_text),
        f"{confidence:.1f}" if confidence is not None else "-",
        ",".join(ocr_flags) if ocr_flags else "-",
    )

    return merge_page_ocr_results(
        page=clean_page,
        image_path=source_image_path,
        ocr_text_path=ocr_path,
        confidence=confidence,
        ocr_text=ocr_text,
        ocr_flags=ocr_flags,
        ocr_warnings=ocr_warnings,
        repo_root=repo_root,
    )


def trial_page_result(
    *,
    updated_page: PageArtifact,
    source_filename: str,
) -> dict[str, object]:
    """Build a compact serializable OCR page result for trial outputs."""
    return {
        "source_filename": source_filename,
        "page_number": updated_page.page_number,
        "extraction_method": updated_page.extraction_method,
        "ocr_char_count": updated_page.ocr_char_count,
        "ocr_confidence": updated_page.ocr_confidence,
        "quality_flags": updated_page.quality_flags,
        "warnings": updated_page.warnings,
        "image_path": updated_page.image_path,
        "ocr_text_path": updated_page.ocr_text_path,
    }


def process_page_ocr_trial(
    *,
    repo_root: Path,
    source_pdf_path: Path,
    source_filename: str,
    page: PageArtifact,
    output_doc_dir: Path,
) -> dict[str, object]:
    """Run OCR for a single page into a trial directory without mutating canonical artifacts."""
    output_pages_dir = output_doc_dir / "pages"
    output_pages_dir.mkdir(parents=True, exist_ok=True)
    updated_page = process_page_ocr(
        pdf_path=source_pdf_path,
        doc_dir=output_doc_dir,
        page=page,
        repo_root=repo_root,
    )
    return trial_page_result(updated_page=updated_page, source_filename=source_filename)


def normalize_document_ocr(manifest_path: Path, repo_root: Path) -> DocumentManifest:
    """Run OCR fallback for one document where manifest heuristics recommend it."""
    manifest = load_manifest(manifest_path)
    pdf_path = absolute_repo_path(repo_root, manifest.source_pdf)
    doc_dir = manifest_path.parent
    target_pages = set(target_page_numbers(manifest))

    if not target_pages:
        LOGGER.info("Skipping OCR for %s | no flagged pages", manifest.source_filename)
        return manifest

    LOGGER.info(
        "Running OCR for %s | target_pages=%s",
        manifest.source_filename,
        ",".join(str(page_number) for page_number in sorted(target_pages)),
    )

    updated_pages: list[PageArtifact] = []
    for page in manifest.pages:
        if page.page_number not in target_pages:
            updated_pages.append(page)
            continue
        try:
            updated_pages.append(process_page_ocr(pdf_path, doc_dir, page, repo_root))
        except Exception as error:
            failed_page = reset_page_ocr_fields(page).model_copy(
                update={
                    "quality_flags": list(dict.fromkeys(page.quality_flags + ["ocr_attempted", "ocr_failed", "llm_repair_recommended"])),
                    "warnings": list(dict.fromkeys(page.warnings + [f"OCR: OCR failed: {error}"])),
                }
            )
            updated_pages.append(failed_page)
            LOGGER.exception(
                "OCR failed for %s page %s",
                manifest.source_filename,
                page.page_number,
            )

    manifest.pages = updated_pages
    manifest.quality_flags = roll_up_doc_ocr_flags(updated_pages, manifest.quality_flags)
    manifest = recompute_manifest_llm_flags(manifest)
    write_manifest(manifest_path, manifest)
    LOGGER.info(
        "Completed OCR for %s | doc_flags=%s",
        manifest.source_filename,
        ",".join(manifest.quality_flags) if manifest.quality_flags else "-",
    )
    return manifest


def iter_ocr_candidate_manifest_paths(processed_contracts_dir: Path) -> Iterable[Path]:
    """Yield manifest paths for documents with at least one OCR-target page."""
    for manifest_path in sorted((doc_dir / "manifest.json" for doc_dir in processed_contracts_dir.iterdir() if doc_dir.is_dir())):
        if not manifest_path.exists():
            continue
        manifest = load_manifest(manifest_path)
        if target_page_numbers(manifest):
            yield manifest_path


def default_ocr_worker_count() -> int:
    """Return a conservative default worker count for canonical OCR execution."""
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count - 1, 4))


def normalize_ocr_documents(
    repo_root: Path,
    processed_contracts_dir: Path,
    *,
    mode: str = "parallel",
    workers: int | None = None,
) -> list[DocumentManifest]:
    """Run OCR fallback for all documents whose manifest flags recommend it."""
    ensure_tesseract_available()
    started_at = time.perf_counter()
    manifest_paths = list(iter_ocr_candidate_manifest_paths(processed_contracts_dir))
    worker_count = workers or default_ocr_worker_count()
    LOGGER.info(
        "Starting OCR normalization | mode=%s | candidates=%s | workers=%s",
        mode,
        len(manifest_paths),
        worker_count,
    )
    manifests: list[DocumentManifest] = []

    if mode == "parallel":
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(normalize_document_ocr, manifest_path, repo_root): manifest_path
                for manifest_path in manifest_paths
            }
            completed = 0
            for future in as_completed(futures):
                manifest_path = futures[future]
                completed += 1
                try:
                    manifests.append(future.result())
                    LOGGER.info(
                        "OCR processing [%s/%s] %s | status=ok",
                        completed,
                        len(manifest_paths),
                        manifest_path.parent.name,
                    )
                except Exception:
                    LOGGER.exception(
                        "OCR processing [%s/%s] %s | status=failed",
                        completed,
                        len(manifest_paths),
                        manifest_path.parent.name,
                    )
                    raise
    else:
        for index, manifest_path in enumerate(manifest_paths, start=1):
            LOGGER.info("OCR processing [%s/%s] %s", index, len(manifest_paths), manifest_path.parent.name)
            manifests.append(normalize_document_ocr(manifest_path, repo_root))

    LOGGER.info(
        "OCR normalization complete: %s documents | elapsed=%.4fs",
        len(manifests),
        time.perf_counter() - started_at,
    )
    return manifests


def build_ocr_report(manifests: Iterable[DocumentManifest]) -> dict[str, object]:
    """Build a compact OCR-stage report for console follow-up and file output."""
    manifest_list = list(manifests)
    attempted = [manifest for manifest in manifest_list if "has_ocr_pages" in manifest.quality_flags]
    llm_recommended = [
        manifest
        for manifest in manifest_list
        if any(flag in manifest.quality_flags for flag in ("llm_markdown_recommended", "llm_repair_recommended"))
    ]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_candidate_documents": len(manifest_list),
        "ocr_attempted_documents": len(attempted),
        "llm_recommended_documents": len(llm_recommended),
        "llm_recommended": [
            {
                "doc_id": manifest.doc_id,
                "source_filename": manifest.source_filename,
                "quality_flags": manifest.quality_flags,
            }
            for manifest in llm_recommended
        ],
    }


def write_ocr_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the OCR summary report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
