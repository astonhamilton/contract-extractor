from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import fitz
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from packages.schemas import DocumentManifest, ExtractionMethod, PageArtifact, ProcessingStatus


LINE_BREAK_RE = re.compile(r"\r\n?")
WHITESPACE_RE = re.compile(r"[ \t]+")
MULTI_BLANK_RE = re.compile(r"\n{3,}")
LOGGER = logging.getLogger(__name__)


def absolute_repo_path(repo_root: Path, repo_relative_path: str) -> Path:
    """Resolve a repo-relative path string into an absolute filesystem path."""
    return repo_root / repo_relative_path


def page_source_image_path(repo_root: Path, page: PageArtifact) -> Path | None:
    """Resolve the original rendered page image path when present."""
    if not page.image_path:
        return None
    return absolute_repo_path(repo_root, page.image_path)


def page_validated_image_path(repo_root: Path, page: PageArtifact) -> Path | None:
    """Resolve the validated upright page image path when present."""
    if not page.validated_image_path:
        return None
    return absolute_repo_path(repo_root, page.validated_image_path)


def preferred_page_image_path(repo_root: Path, page: PageArtifact) -> Path | None:
    """Resolve the best page image path for downstream OCR/vision use."""
    validated = page_validated_image_path(repo_root, page)
    if validated and validated.exists():
        return validated
    source = page_source_image_path(repo_root, page)
    if source and source.exists():
        return source
    return validated or source


def repo_relative_path(path: Path, repo_root: Path) -> str:
    """Convert an absolute path to a repo-relative string for serialization."""
    return str(path.relative_to(repo_root))


def load_manifest(manifest_path: Path) -> DocumentManifest:
    """Load and validate a document manifest from disk."""
    return DocumentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))


def write_manifest(manifest_path: Path, manifest: DocumentManifest) -> None:
    """Write a validated manifest back to disk."""
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )


def iter_manifest_paths(processed_contracts_dir: Path) -> Iterable[Path]:
    """Yield manifest paths for processed document folders."""
    for doc_dir in sorted(processed_contracts_dir.iterdir()):
        if not doc_dir.is_dir():
            continue
        manifest_path = doc_dir / "manifest.json"
        if manifest_path.exists():
            yield manifest_path


def normalize_page_text(raw_text: str | None) -> str:
    """Apply light deterministic cleanup to extracted page text."""
    text = raw_text or ""
    text = LINE_BREAK_RE.sub("\n", text)
    text = WHITESPACE_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip()


def alpha_ratio(text: str) -> float:
    """Compute the ratio of alphabetic characters to all non-whitespace characters."""
    compact = "".join(char for char in text if not char.isspace())
    if not compact:
        return 0.0
    alpha_chars = sum(1 for char in compact if char.isalpha())
    return alpha_chars / len(compact)


def symbol_ratio(text: str) -> float:
    """Compute the ratio of symbol-like characters to all non-whitespace characters."""
    compact = "".join(char for char in text if not char.isspace())
    if not compact:
        return 0.0
    symbol_chars = sum(1 for char in compact if not char.isalnum())
    return symbol_chars / len(compact)


def newline_ratio(text: str) -> float:
    """Compute the density of newlines relative to overall text length."""
    if not text:
        return 0.0
    return text.count("\n") / len(text)


def page_has_images(page) -> bool:
    """Best-effort check for image XObjects on a PDF page."""
    try:
        resources = page.get("/Resources")
        if not resources:
            return False
        xobject_ref = resources.get("/XObject")
        if not xobject_ref:
            return False
        xobjects = xobject_ref.get_object()
        for value in xobjects.values():
            xobject = value.get_object()
            if xobject.get("/Subtype") == "/Image":
                return True
    except Exception:
        return False
    return False


def page_quality_signals(text: str, has_images: bool) -> tuple[list[str], list[str]]:
    """Derive machine-friendly quality flags and human-readable warnings."""
    flags: list[str] = []
    warnings: list[str] = []

    char_count = len(text)
    if char_count == 0:
        flags.append("no_text_extracted")
        warnings.append("No text was extracted from this page.")

    if 0 < char_count < 40:
        flags.append("low_text_density")
        warnings.append("Very little text was extracted from this page.")

    if has_images and char_count == 0:
        flags.extend(["suspected_image_only_page", "suspected_scanned_page"])
        warnings.append("Page appears image-based and may require OCR.")

    if has_images and char_count < 40:
        flags.append("image_render_recommended")

    if alpha_ratio(text) < 0.35 and char_count >= 40:
        flags.append("suspected_garbled_text")
        warnings.append("Extracted text appears low-quality or garbled.")

    if symbol_ratio(text) > 0.35 and char_count >= 40:
        flags.append("high_symbol_ratio")

    if newline_ratio(text) > 0.12 and char_count >= 80:
        flags.append("high_whitespace_noise")

    lowered = text.lower()
    if char_count < 120 and any(token in lowered for token in ("page ", "county", "contract", "agreement")):
        flags.append("possible_header_footer_only")

    if "\t" in text or "  " in text or "|" in text:
        flags.append("possible_table_or_form_content")

    if any(flag in flags for flag in ("no_text_extracted", "suspected_scanned_page", "suspected_garbled_text")):
        flags.append("ocr_recommended")

    deduped_flags = list(dict.fromkeys(flags))
    deduped_warnings = list(dict.fromkeys(warnings))
    return deduped_flags, deduped_warnings


def document_quality_flags(page_flags: Iterable[list[str]]) -> list[str]:
    """Roll up page-level quality flags into document-level indicators."""
    page_flags_list = list(page_flags)
    flattened = [flag for flags in page_flags_list for flag in flags]
    doc_flags: list[str] = []

    if any(flag in flattened for flag in ("low_text_density", "suspected_garbled_text")):
        doc_flags.append("has_low_quality_pages")
    if "suspected_scanned_page" in flattened:
        doc_flags.append("has_scanned_pages")
    if "ocr_recommended" in flattened:
        doc_flags.append("ocr_recommended")

    total_pages = max(len(page_flags_list), 1)
    scanned_pages = flattened.count("suspected_scanned_page")
    if scanned_pages and scanned_pages >= total_pages / 2:
        doc_flags.append("mostly_image_based")
    page_profiles = {tuple(sorted(flags)) for flags in page_flags_list}
    if len(page_profiles) > 1:
        doc_flags.append("mixed_text_quality")
    if any(flag in flattened for flag in ("suspected_scanned_page", "suspected_garbled_text")):
        doc_flags.append("manual_review_recommended")

    return list(dict.fromkeys(doc_flags))


def page_text_output_path(doc_dir: Path, page_number: int) -> Path:
    """Return the canonical page text output path for a page number."""
    return doc_dir / "pages" / f"{page_number:04d}.txt"


def page_image_output_path(doc_dir: Path, page_number: int) -> Path:
    """Return the canonical page image output path for a page number."""
    return doc_dir / "pages" / f"{page_number:04d}.png"


def render_page_image(pdf_path: Path, page_number: int, image_path: Path) -> None:
    """Render one PDF page to a PNG image."""
    document = fitz.open(pdf_path)
    try:
        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pixmap.save(image_path)
    finally:
        document.close()


def should_generate_page_image(flags: list[str]) -> bool:
    """Return whether normalize_txt should emit a page image artifact."""
    flag_set = set(flags)
    return bool(flag_set & {"image_render_recommended", "ocr_recommended"})


def txt_page_is_complete(page: PageArtifact, repo_root: Path) -> bool:
    """Return whether a page already has the text-stage artifacts it currently needs."""
    if not page.text_path:
        return False
    text_path = absolute_repo_path(repo_root, page.text_path)
    if not text_path.exists():
        return False

    if should_generate_page_image(page.quality_flags):
        if not page.image_path:
            return False
        image_path = absolute_repo_path(repo_root, page.image_path)
        if not image_path.exists():
            return False

    return True


def document_txt_is_complete(manifest: DocumentManifest, repo_root: Path) -> bool:
    """Return whether a document already has all required text-stage artifacts."""
    if manifest.processing_status.status != ProcessingStatus.COMPLETED:
        return False
    if not manifest.pages:
        return False
    return all(txt_page_is_complete(page, repo_root) for page in manifest.pages)


def fallback_page_flags() -> tuple[list[str], list[str]]:
    """Return default page flags for render-first fallback pages."""
    flags = [
        "no_text_extracted",
        "suspected_image_only_page",
        "suspected_scanned_page",
        "image_render_recommended",
        "ocr_recommended",
    ]
    warnings = [
        "No text was extracted from this page.",
        "Page was recovered via render-first fallback after text extraction failed.",
    ]
    return flags, warnings


def render_first_fallback_document(
    *,
    manifest: DocumentManifest,
    manifest_path: Path,
    repo_root: Path,
    source_pdf_path: Path,
    doc_dir: Path,
) -> DocumentManifest:
    """Recover a document into page artifacts by rendering page images when text extraction fails."""
    LOGGER.info("Falling back to render-first normalization for %s", manifest.source_filename)
    document = fitz.open(source_pdf_path)
    try:
        page_artifacts: list[PageArtifact] = []
        collected_flags: list[list[str]] = []
        for page_number in range(1, document.page_count + 1):
            text_output_path = page_text_output_path(doc_dir, page_number)
            image_output_path = page_image_output_path(doc_dir, page_number)
            text_output_path.write_text("", encoding="utf-8")
            render_page_image(source_pdf_path, page_number, image_output_path)
            flags, warnings = fallback_page_flags()
            collected_flags.append(flags)
            page_artifacts.append(
                PageArtifact(
                    page_number=page_number,
                    text_path=repo_relative_path(text_output_path, repo_root),
                    image_path=repo_relative_path(image_output_path, repo_root),
                    extraction_method=ExtractionMethod.PDF_TEXT,
                    char_count=0,
                    warnings=warnings,
                    quality_flags=flags,
                )
            )
    finally:
        document.close()

    manifest.page_count = len(page_artifacts)
    manifest.has_text_layer = False
    manifest.pages = page_artifacts
    manifest.quality_flags = list(
        dict.fromkeys(document_quality_flags(collected_flags) + ["render_first_fallback"])
    )
    manifest.processing_status.status = ProcessingStatus.COMPLETED
    manifest.processing_status.error = None
    manifest.processing_status.warnings = list(
        dict.fromkeys(manifest.processing_status.warnings + ["Recovered via render-first fallback."])
    )
    write_manifest(manifest_path, manifest)
    LOGGER.info(
        "Completed %s via render-first fallback | pages=%s | doc_flags=%s",
        manifest.source_filename,
        manifest.page_count,
        ",".join(manifest.quality_flags) if manifest.quality_flags else "-",
    )
    return manifest


def normalize_document(manifest_path: Path, repo_root: Path) -> DocumentManifest:
    """Normalize one document into page-level text artifacts and update its manifest."""
    manifest = load_manifest(manifest_path)
    source_pdf_path = absolute_repo_path(repo_root, manifest.source_pdf)
    doc_dir = manifest_path.parent
    pages_dir = doc_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    if document_txt_is_complete(manifest, repo_root):
        LOGGER.info("Skipping %s | text-stage artifacts already present", manifest.source_filename)
        return manifest

    manifest.processing_status.status = ProcessingStatus.RUNNING
    manifest.processing_status.error = None
    manifest.processing_status.warnings = []

    LOGGER.info("Normalizing %s", manifest.source_filename)

    try:
        reader = PdfReader(str(source_pdf_path))
    except PdfReadError as error:
        LOGGER.warning("pypdf open failed for %s: %s", manifest.source_filename, error)
        try:
            return render_first_fallback_document(
                manifest=manifest,
                manifest_path=manifest_path,
                repo_root=repo_root,
                source_pdf_path=source_pdf_path,
                doc_dir=doc_dir,
            )
        except Exception as fallback_error:
            manifest.processing_status.status = ProcessingStatus.FAILED
            manifest.processing_status.error = f"Failed to read PDF: {error}; render fallback failed: {fallback_error}"
            write_manifest(manifest_path, manifest)
            LOGGER.error("Failed to read %s: %s", manifest.source_filename, error)
            LOGGER.exception("Render-first fallback also failed for %s", manifest.source_filename)
            return manifest

    page_artifacts: list[PageArtifact] = []
    collected_flags: list[list[str]] = []
    has_any_text = False
    existing_pages = {page.page_number: page for page in manifest.pages}

    try:
        for page_number, page in enumerate(reader.pages, start=1):
            existing_page = existing_pages.get(page_number)
            if existing_page and txt_page_is_complete(existing_page, repo_root):
                collected_flags.append(existing_page.quality_flags)
                has_any_text = has_any_text or existing_page.char_count > 0
                LOGGER.info(
                    "Page %s | skipped | text-stage artifacts already present",
                    page_number,
                )
                page_artifacts.append(existing_page)
                continue

            normalized_text = normalize_page_text(page.extract_text())
            output_path = page_text_output_path(doc_dir, page_number)
            output_path.write_text(normalized_text + ("\n" if normalized_text else ""), encoding="utf-8")

            has_images = page_has_images(page)
            flags, warnings = page_quality_signals(normalized_text, has_images)
            image_path = None
            if should_generate_page_image(flags):
                image_output_path = page_image_output_path(doc_dir, page_number)
                render_page_image(source_pdf_path, page_number, image_output_path)
                image_path = repo_relative_path(image_output_path, repo_root)
            collected_flags.append(flags)
            has_any_text = has_any_text or bool(normalized_text)

            LOGGER.info(
                "Page %s | chars=%s | flags=%s",
                page_number,
                len(normalized_text),
                ",".join(flags) if flags else "-",
            )

            page_artifacts.append(
                PageArtifact(
                    page_number=page_number,
                    text_path=repo_relative_path(output_path, repo_root),
                    image_path=image_path,
                    extraction_method=ExtractionMethod.PDF_TEXT,
                    char_count=len(normalized_text),
                    warnings=warnings,
                    quality_flags=flags,
                )
            )
    except PdfReadError as error:
        LOGGER.warning("pypdf page extraction failed for %s: %s", manifest.source_filename, error)
        try:
            return render_first_fallback_document(
                manifest=manifest,
                manifest_path=manifest_path,
                repo_root=repo_root,
                source_pdf_path=source_pdf_path,
                doc_dir=doc_dir,
            )
        except Exception as fallback_error:
            manifest.processing_status.status = ProcessingStatus.FAILED
            manifest.processing_status.error = f"Failed during page extraction: {error}; render fallback failed: {fallback_error}"
            manifest.quality_flags = ["pdf_read_error", "manual_review_recommended"]
            write_manifest(manifest_path, manifest)
            LOGGER.error("Failed during page extraction for %s: %s", manifest.source_filename, error)
            LOGGER.exception("Render-first fallback also failed for %s", manifest.source_filename)
            return manifest
    except Exception as error:
        LOGGER.warning("Unexpected text normalization failure for %s: %s", manifest.source_filename, error)
        try:
            return render_first_fallback_document(
                manifest=manifest,
                manifest_path=manifest_path,
                repo_root=repo_root,
                source_pdf_path=source_pdf_path,
                doc_dir=doc_dir,
            )
        except Exception as fallback_error:
            manifest.processing_status.status = ProcessingStatus.FAILED
            manifest.processing_status.error = f"Unexpected normalization error: {error}; render fallback failed: {fallback_error}"
            manifest.quality_flags = ["unexpected_normalization_error", "manual_review_recommended"]
            write_manifest(manifest_path, manifest)
            LOGGER.exception("Unexpected normalization failure for %s", manifest.source_filename)
            LOGGER.exception("Render-first fallback also failed for %s", manifest.source_filename)
            return manifest

    manifest.page_count = len(page_artifacts)
    manifest.has_text_layer = has_any_text
    manifest.pages = page_artifacts
    manifest.quality_flags = document_quality_flags(collected_flags)
    manifest.processing_status.status = ProcessingStatus.COMPLETED

    write_manifest(manifest_path, manifest)
    LOGGER.info(
        "Completed %s | pages=%s | doc_flags=%s",
        manifest.source_filename,
        manifest.page_count,
        ",".join(manifest.quality_flags) if manifest.quality_flags else "-",
    )
    return manifest


def normalize_all_documents(repo_root: Path, processed_contracts_dir: Path) -> list[DocumentManifest]:
    """Normalize every inventoried document under the processed contracts folder."""
    manifest_paths = list(iter_manifest_paths(processed_contracts_dir))
    LOGGER.info("Starting normalization for %s documents", len(manifest_paths))
    manifests: list[DocumentManifest] = []

    for index, manifest_path in enumerate(manifest_paths, start=1):
        LOGGER.info("Processing [%s/%s] %s", index, len(manifest_paths), manifest_path.parent.name)
        manifests.append(normalize_document(manifest_path, repo_root))

    LOGGER.info("Normalization complete: %s documents", len(manifests))
    return manifests


def build_normalization_report(manifests: Iterable[DocumentManifest]) -> dict[str, object]:
    """Build a compact normalization summary for quick run inspection."""
    manifest_list = list(manifests)
    completed = [manifest for manifest in manifest_list if manifest.processing_status.status == ProcessingStatus.COMPLETED]
    failed = [manifest for manifest in manifest_list if manifest.processing_status.status == ProcessingStatus.FAILED]
    ocr_recommended = [manifest for manifest in manifest_list if "ocr_recommended" in manifest.quality_flags]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_documents": len(manifest_list),
        "completed_documents": len(completed),
        "failed_documents": len(failed),
        "ocr_recommended_documents": len(ocr_recommended),
        "failed": [
            {
                "doc_id": manifest.doc_id,
                "source_filename": manifest.source_filename,
                "error": manifest.processing_status.error,
            }
            for manifest in failed
        ],
        "ocr_recommended": [
            {
                "doc_id": manifest.doc_id,
                "source_filename": manifest.source_filename,
                "quality_flags": manifest.quality_flags,
            }
            for manifest in ocr_recommended
        ],
    }


def write_normalization_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the normalization summary report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
