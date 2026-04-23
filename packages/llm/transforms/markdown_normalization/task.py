from __future__ import annotations

import logging
from pathlib import Path

from packages.llm.transforms.markdown_normalization.config import MarkdownNormalizationConfig
from packages.llm.transforms.markdown_normalization.parse import clean_markdown_output
from packages.llm.transforms.markdown_normalization.prompt import markdown_system_prompt
from packages.llm.shared.task_runtime.content import (
    build_markdown_user_content,
    read_optional_text,
)
from packages.llm.shared.task_runtime.text import stream_completion_text
from packages.schemas.llm_normalization import (
    LLMNormalizationInput,
    LLMNormalizationMode,
    LLMNormalizationResult,
)


LOGGER = logging.getLogger(__name__)


def build_markdown_input(
    *,
    doc_id: str,
    source_filename: str,
    page_number: int,
    model: str,
    quality_flags: list[str],
    image_path: Path | None,
    pdf_text_path: Path | None,
    ocr_text_path: Path | None,
) -> LLMNormalizationInput:
    """Build the typed input contract for one markdown normalization request."""
    return LLMNormalizationInput(
        doc_id=doc_id,
        source_filename=source_filename,
        page_number=page_number,
        mode=LLMNormalizationMode.MARKDOWN,
        model=model,
        image_path=str(image_path) if image_path and image_path.exists() else None,
        pdf_text_path=str(pdf_text_path) if pdf_text_path and pdf_text_path.exists() else None,
        ocr_text_path=str(ocr_text_path) if ocr_text_path and ocr_text_path.exists() else None,
        quality_flags=quality_flags,
    )


def run_markdown_normalization(
    request: LLMNormalizationInput,
    config: MarkdownNormalizationConfig,
    progress_callback=None,
) -> LLMNormalizationResult:
    """Run one markdown normalization call and return a typed result."""
    image_path = Path(request.image_path) if request.image_path else None
    pdf_text = read_optional_text(Path(request.pdf_text_path)) if request.pdf_text_path else None
    ocr_text = read_optional_text(Path(request.ocr_text_path)) if request.ocr_text_path else None

    LOGGER.info(
        "LLM markdown normalization | file=%s | page=%s | image=%s | pdf_text=%s | ocr_text=%s | flags=%s",
        request.source_filename,
        request.page_number,
        bool(image_path and image_path.exists()),
        bool(pdf_text),
        bool(ocr_text),
        ",".join(request.quality_flags) if request.quality_flags else "-",
    )

    user_content = build_markdown_user_content(
        image_path=image_path,
        pdf_text=pdf_text,
        ocr_text=ocr_text,
        quality_flags=request.quality_flags,
    )
    messages = [
        {"role": "system", "content": markdown_system_prompt()},
        {"role": "user", "content": user_content},
    ]
    raw_output = stream_completion_text(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        progress_callback=progress_callback,
    )
    cleaned_output = clean_markdown_output(raw_output)
    LOGGER.info(
        "LLM markdown normalization complete | file=%s | page=%s | output_chars=%s",
        request.source_filename,
        request.page_number,
        len(cleaned_output),
    )
    return LLMNormalizationResult(
        doc_id=request.doc_id,
        source_filename=request.source_filename,
        page_number=request.page_number,
        mode=LLMNormalizationMode.MARKDOWN,
        model=config.model,
        output_markdown=cleaned_output,
        prompt_version=config.prompt_version,
    )
