from __future__ import annotations

from collections.abc import Iterable

from packages.schemas import DocumentManifest, PageArtifact


TABLE_MARKDOWN_FLAGS = {
    "possible_table_or_form_content",
    "ocr_possible_table_or_form_content",
}

IMAGE_LLM_SKIP_FLAGS = {
    "likely_blank_page",
    "likely_low_information_page",
    "skip_llm_repair",
}

REPAIR_SKIP_FLAGS = set(IMAGE_LLM_SKIP_FLAGS)

PAGE_LLM_RECOMMENDATION_FLAGS = {
    "llm_markdown_recommended",
    "llm_repair_recommended",
    "llm_vision_markdown_recommended",
    "llm_normalization_recommended",
}

DOC_LLM_RECOMMENDATION_FLAGS = {
    "llm_markdown_recommended",
    "llm_repair_recommended",
    "llm_vision_markdown_recommended",
    "llm_normalization_recommended",
    "ocr_still_needs_review",
}


def page_record(manifest: DocumentManifest, page: PageArtifact) -> dict[str, object]:
    """Create a compact page record for report and sampling outputs."""
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


def is_markdown_candidate(page: PageArtifact) -> bool:
    """Return whether a page should be targeted for markdown/layout LLM normalization."""
    if page.markdown_path:
        return False
    flags = set(page.quality_flags)
    if flags & IMAGE_LLM_SKIP_FLAGS:
        return False
    if not flags & TABLE_MARKDOWN_FLAGS:
        return False

    return bool(
        page.ocr_text_path
        or "suspected_scanned_page" in flags
        or "suspected_image_only_page" in flags
        or "ocr_low_confidence" in flags
        or "ocr_high_whitespace_noise" in flags
        or "ocr_improved_over_pdf_text" in flags
    )


def is_repair_candidate(page: PageArtifact) -> bool:
    """Return whether a page should be targeted for repair LLM normalization."""
    if page.repair_markdown_path:
        return False
    flags = set(page.quality_flags)
    if flags & REPAIR_SKIP_FLAGS:
        return False

    return bool(
        "ocr_failed" in flags
        or "ocr_possible_handwriting" in flags
        or ("ocr_low_confidence" in flags and "ocr_not_better_than_pdf_text" in flags)
        or ("ocr_suspected_garbled_text" in flags and "ocr_not_better_than_pdf_text" in flags)
        or ("no_text_extracted" in flags and "ocr_recommended" in flags and not page.ocr_text_path)
        or ("suspected_garbled_text" in flags and not page.ocr_text_path)
    )


def is_vision_markdown_candidate(page: PageArtifact) -> bool:
    """Return whether a page should be targeted for image-led markdown normalization."""
    if page.vision_markdown_path or not page.image_path:
        return False
    flags = set(page.quality_flags)
    if flags & IMAGE_LLM_SKIP_FLAGS:
        return False
    return bool(
        "suspected_scanned_page" in flags
        or "suspected_image_only_page" in flags
        or "no_text_extracted" in flags
        or "ocr_low_confidence" in flags
        or "ocr_failed" in flags
        or "possible_table_or_form_content" in flags
        or "ocr_possible_table_or_form_content" in flags
    )


def is_skipped_repair_page(page: PageArtifact) -> bool:
    """Return whether a page should be excluded from repair LLM work."""
    return bool(set(page.quality_flags) & REPAIR_SKIP_FLAGS)


def is_skipped_image_llm_page(page: PageArtifact) -> bool:
    """Return whether a page should be excluded from image-based LLM work."""
    return bool(set(page.quality_flags) & IMAGE_LLM_SKIP_FLAGS)


def markdown_candidates(manifests: Iterable[DocumentManifest]) -> list[dict[str, object]]:
    """Return compact page records for markdown candidates."""
    candidates: list[dict[str, object]] = []
    for manifest in manifests:
        for page in manifest.pages:
            if is_markdown_candidate(page):
                candidates.append(page_record(manifest, page))
    return candidates


def repair_candidates(manifests: Iterable[DocumentManifest]) -> list[dict[str, object]]:
    """Return compact page records for repair candidates."""
    candidates: list[dict[str, object]] = []
    for manifest in manifests:
        for page in manifest.pages:
            if is_repair_candidate(page):
                candidates.append(page_record(manifest, page))
    return candidates


def skipped_repair_pages(manifests: Iterable[DocumentManifest]) -> list[dict[str, object]]:
    """Return compact page records for skipped repair pages."""
    pages: list[dict[str, object]] = []
    for manifest in manifests:
        for page in manifest.pages:
            if is_skipped_repair_page(page):
                pages.append(page_record(manifest, page))
    return pages


def vision_markdown_candidates(manifests: Iterable[DocumentManifest]) -> list[dict[str, object]]:
    """Return compact page records for vision-markdown candidates."""
    candidates: list[dict[str, object]] = []
    for manifest in manifests:
        for page in manifest.pages:
            if is_vision_markdown_candidate(page):
                candidates.append(page_record(manifest, page))
    return candidates


def recompute_page_llm_flags(page: PageArtifact) -> PageArtifact:
    """Recompute page-level LLM recommendation flags from current page state."""
    base_flags = [flag for flag in page.quality_flags if flag not in PAGE_LLM_RECOMMENDATION_FLAGS]
    updated_flags = list(base_flags)

    if is_markdown_candidate(page):
        updated_flags.append("llm_markdown_recommended")
    if is_repair_candidate(page):
        updated_flags.append("llm_repair_recommended")
    if is_vision_markdown_candidate(page):
        updated_flags.append("llm_vision_markdown_recommended")

    return page.model_copy(update={"quality_flags": list(dict.fromkeys(updated_flags))})


def roll_up_doc_llm_flags(pages: list[PageArtifact], base_flags: list[str]) -> list[str]:
    """Recompute document-level LLM recommendation flags from current page state."""
    flags = [flag for flag in base_flags if flag not in DOC_LLM_RECOMMENDATION_FLAGS]

    if any("llm_markdown_recommended" in page.quality_flags for page in pages):
        flags.append("llm_markdown_recommended")
    if any("llm_repair_recommended" in page.quality_flags for page in pages):
        flags.extend(["llm_repair_recommended", "ocr_still_needs_review"])
    if any("llm_vision_markdown_recommended" in page.quality_flags for page in pages):
        flags.append("llm_vision_markdown_recommended")

    return list(dict.fromkeys(flags))


def recompute_manifest_llm_flags(manifest: DocumentManifest) -> DocumentManifest:
    """Recompute page- and doc-level LLM recommendation flags for one manifest."""
    updated_pages = [recompute_page_llm_flags(page) for page in manifest.pages]
    return manifest.model_copy(
        update={
            "pages": updated_pages,
            "quality_flags": roll_up_doc_llm_flags(updated_pages, manifest.quality_flags),
        }
    )
