from __future__ import annotations

from packages.schemas import DocumentManifest, PageArtifact


OCR_TRIGGER_FLAGS = {
    "ocr_recommended",
    "image_render_recommended",
    "suspected_scanned_page",
    "suspected_image_only_page",
    "no_text_extracted",
    "suspected_garbled_text",
}


def page_should_run_ocr(page: PageArtifact) -> bool:
    """Return whether a page still needs OCR fallback.

    OCR routing is based on the original text-pass trigger flags, but once OCR has
    already produced an OCR text artifact for a page we should not keep treating
    it as an outstanding OCR target. Subsequent stages decide whether the
    post-OCR result still needs LLM work.
    """
    flags = set(page.quality_flags)
    if page.ocr_text_path:
        return False
    return bool(flags & OCR_TRIGGER_FLAGS)


def target_page_numbers(manifest: DocumentManifest) -> list[int]:
    """Return page numbers that should be processed by OCR fallback."""
    return [page.page_number for page in manifest.pages if page_should_run_ocr(page)]
