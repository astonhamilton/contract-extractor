from __future__ import annotations

from typing import Literal

from pydantic import Field

from packages.schemas.common import BaseSchema


RotationDegrees = Literal[0, 90, 180, 270]


class ImageOrientationDecisionInput(BaseSchema):
    doc_id: str
    source_filename: str
    page_number: int = Field(ge=1)
    model: str
    image_path: str
    quality_flags: list[str] = Field(default_factory=list)


class ImageOrientationDecisionModelOutput(BaseSchema):
    rotation_degrees: RotationDegrees
    is_already_upright: bool
    needs_manual_review: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    visual_cues: list[str] = Field(default_factory=list)


class ImageOrientationDecision(BaseSchema):
    doc_id: str
    source_filename: str
    page_number: int = Field(ge=1)
    model: str
    rotation_degrees: RotationDegrees
    is_already_upright: bool
    needs_manual_review: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    visual_cues: list[str] = Field(default_factory=list)
    prompt_version: str


class ImageOrientationTrialJudgment(BaseSchema):
    correct_rotation: RotationDegrees | None = None
    acceptable: bool | None = None
    notes: str = ""
