from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from packages.schemas.common import BaseSchema


class LLMNormalizationMode(StrEnum):
    MARKDOWN = "markdown"
    REPAIR = "repair"
    VISION_MARKDOWN = "vision_markdown"


class LLMNormalizationInput(BaseSchema):
    doc_id: str
    source_filename: str
    page_number: int = Field(ge=1)
    mode: LLMNormalizationMode
    model: str
    image_path: str | None = None
    pdf_text_path: str | None = None
    ocr_text_path: str | None = None
    quality_flags: list[str] = Field(default_factory=list)


class LLMNormalizationResult(BaseSchema):
    doc_id: str
    source_filename: str
    page_number: int = Field(ge=1)
    mode: LLMNormalizationMode
    model: str
    output_markdown: str | None = None
    output_text: str | None = None
    prompt_version: str
    streamed: bool = True
    warnings: list[str] = Field(default_factory=list)


class LLMTrialJudgment(BaseSchema):
    mode: LLMNormalizationMode
    useful: bool | None = None
    hallucinated: bool | None = None
    better_than_ocr: bool | None = None
    ready_for_pipeline: bool | None = None
    notes: str = ""
