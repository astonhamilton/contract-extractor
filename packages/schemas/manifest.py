from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from packages.schemas.common import BaseSchema, StageStatus


class ArtifactKind(StrEnum):
    TEXT = "text"
    MARKDOWN = "markdown"
    IMAGE = "image"
    JSON = "json"
    PDF = "pdf"
    XML = "xml"


class ExtractionMethod(StrEnum):
    PDF_TEXT = "pdf_text"
    OCR = "ocr"
    VISION = "vision"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class PageArtifact(BaseSchema):
    page_number: int = Field(ge=1)
    text_path: str | None = None
    ocr_text_path: str | None = None
    markdown_path: str | None = None
    vision_markdown_path: str | None = None
    repair_markdown_path: str | None = None
    image_path: str | None = None
    validated_image_path: str | None = None
    image_rotation_degrees: int | None = None
    image_orientation_method: str | None = None
    extraction_method: ExtractionMethod = ExtractionMethod.UNKNOWN
    char_count: int = Field(default=0, ge=0)
    ocr_char_count: int = Field(default=0, ge=0)
    ocr_confidence: float | None = Field(default=None, ge=0.0, le=100.0)
    warnings: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)


class DerivedArtifact(BaseSchema):
    kind: ArtifactKind
    path: str
    description: str | None = None


class DocumentManifest(BaseSchema):
    doc_id: str
    source_pdf: str
    source_filename: str
    sha256: str | None = None
    page_count: int = Field(default=0, ge=0)
    has_text_layer: bool | None = None
    quality_flags: list[str] = Field(default_factory=list)
    processing_status: StageStatus = Field(default_factory=StageStatus)
    procurement_context_path: str | None = None
    procurement_context_status: StageStatus = Field(default_factory=StageStatus)
    classification_path: str | None = None
    classification_status: StageStatus = Field(default_factory=StageStatus)
    change_extraction_path: str | None = None
    change_extraction_status: StageStatus = Field(default_factory=StageStatus)
    governing_domain_notes_path: str | None = None
    governing_domain_notes_status: StageStatus = Field(default_factory=StageStatus)
    page_notes_path: str | None = None
    page_notes_status: StageStatus = Field(default_factory=StageStatus)
    pages: list[PageArtifact] = Field(default_factory=list)
    derived_artifacts: list[DerivedArtifact] = Field(default_factory=list)
