from __future__ import annotations

import base64
from pathlib import Path


def read_optional_text(path: Path | None) -> str | None:
    """Read text from a path if it exists, otherwise return None."""
    if path is None or not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip() or None


def image_path_to_data_url(image_path: Path) -> str:
    """Encode a local image as a data URL for multimodal model input."""
    mime_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }.get(image_path.suffix.lower(), "image/png")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_markdown_user_content(
    image_path: Path | None,
    pdf_text: str | None,
    ocr_text: str | None,
    quality_flags: list[str],
) -> list[dict[str, object]]:
    """Build a multimodal user content payload for markdown normalization."""
    parts: list[dict[str, object]] = []

    if image_path and image_path.exists():
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": image_path_to_data_url(image_path)},
            }
        )

    context_sections = [
        "You are normalizing one contract page into faithful markdown.",
        f"Quality flags: {', '.join(quality_flags) if quality_flags else '-'}",
        "",
        "PDF text:",
        pdf_text or "[missing]",
        "",
        "OCR text:",
        ocr_text or "[missing]",
    ]
    parts.append({"type": "text", "text": "\n".join(context_sections)})
    return parts


def build_repair_user_content(
    image_path: Path | None,
    pdf_text: str | None,
    ocr_text: str | None,
    quality_flags: list[str],
) -> list[dict[str, object]]:
    """Build a multimodal user content payload for repair normalization."""
    parts: list[dict[str, object]] = []

    if image_path and image_path.exists():
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": image_path_to_data_url(image_path)},
            }
        )

    context_sections = [
        "You are interpreting one difficult contract page into faithful markdown with separate commentary and transcription.",
        f"Quality flags: {', '.join(quality_flags) if quality_flags else '-'}",
        "",
        "Important requirements:",
        "- Commentary must be clearly labeled as commentary, not literal page text.",
        "- Any readable text should be transcribed faithfully.",
        "- If the page contains table or form structure, preserve it in markdown.",
        "- If the page is effectively blank or low-information, say so plainly in the commentary section.",
        "",
        "PDF text:",
        pdf_text or "[missing]",
        "",
        "OCR text:",
        ocr_text or "[missing]",
    ]
    parts.append({"type": "text", "text": "\n".join(context_sections)})
    return parts


def build_vision_markdown_user_content(
    image_path: Path,
    pdf_text: str | None,
    ocr_text: str | None,
    quality_flags: list[str],
) -> list[dict[str, object]]:
    """Build a multimodal user content payload for image-led markdown conversion."""
    parts: list[dict[str, object]] = [
        {
            "type": "image_url",
            "image_url": {"url": image_path_to_data_url(image_path)},
        }
    ]

    context_sections = [
        "You are converting one contract page image into faithful markdown.",
        "Treat the image as the primary source of truth.",
        "Use OCR/PDF text only as weak hints when they help disambiguate hard-to-read text.",
        f"Quality flags: {', '.join(quality_flags) if quality_flags else '-'}",
        "",
        "Important requirements:",
        "- Return markdown only.",
        "- Keep page-local structure only; do not infer missing content from other pages.",
        "- Preserve headings, lists, tables, checkbox groups, and signature blocks where visible.",
        "- Do not invent unreadable values; preserve uncertainty inline instead.",
        "",
        "PDF text hint:",
        pdf_text or "[missing]",
        "",
        "OCR text hint:",
        ocr_text or "[missing]",
    ]
    parts.append({"type": "text", "text": "\n".join(context_sections)})
    return parts
