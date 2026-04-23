from __future__ import annotations

import logging
from pathlib import Path

from packages.llm.shared.strict_schema import enforce_openai_strict_required
from packages.llm.shared.task_runtime.content import image_path_to_data_url
from packages.llm.shared.task_runtime.structured import completion_json_schema
from packages.llm.transforms.image_orientation_decision.config import ImageOrientationDecisionConfig
from packages.llm.transforms.image_orientation_decision.prompt import image_orientation_system_prompt
from packages.schemas import (
    ImageOrientationDecision,
    ImageOrientationDecisionInput,
    ImageOrientationDecisionModelOutput,
)


LOGGER = logging.getLogger(__name__)


def build_image_orientation_input(
    *,
    doc_id: str,
    source_filename: str,
    page_number: int,
    model: str,
    image_path: Path,
    quality_flags: list[str] | None = None,
) -> ImageOrientationDecisionInput:
    """Build the typed input contract for one image-orientation request."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    return ImageOrientationDecisionInput(
        doc_id=doc_id,
        source_filename=source_filename,
        page_number=page_number,
        model=model,
        image_path=str(image_path),
        quality_flags=quality_flags or [],
    )


def build_image_orientation_user_content(request: ImageOrientationDecisionInput) -> list[dict[str, object]]:
    """Build a multimodal user content payload for one image-orientation decision."""
    quality_flags = ", ".join(request.quality_flags) if request.quality_flags else "-"
    return [
        {
            "type": "image_url",
            "image_url": {"url": image_path_to_data_url(Path(request.image_path))},
        },
        {
            "type": "text",
            "text": "\n".join(
                [
                    "Decide the clockwise rotation needed to make this page upright.",
                    f"doc_id: {request.doc_id}",
                    f"source_filename: {request.source_filename}",
                    f"page_number: {request.page_number}",
                    f"quality_flags: {quality_flags}",
                    "",
                    "Output guidance:",
                    "- rotation_degrees is the clockwise rotation needed from the current image.",
                    "- If the page already looks upright, choose 0.",
                    "- If evidence is mixed, choose the most reasonable rotation and set needs_manual_review=true.",
                    "- Keep the reason short and concrete.",
                ]
            ),
        },
    ]


def run_image_orientation_decision(
    request: ImageOrientationDecisionInput,
    config: ImageOrientationDecisionConfig,
    *,
    debug_dump_dir: str | None = None,
) -> ImageOrientationDecision:
    """Run one image-orientation decision call and return a validated artifact."""
    LOGGER.info(
        "LLM image orientation | file=%s | page=%s",
        request.source_filename,
        request.page_number,
    )
    messages = [
        {"role": "system", "content": image_orientation_system_prompt()},
        {"role": "user", "content": build_image_orientation_user_content(request)},
    ]
    schema = enforce_openai_strict_required(ImageOrientationDecisionModelOutput.model_json_schema())
    payload = completion_json_schema(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        reasoning_effort=config.reasoning_effort,
        schema_name="image_orientation_decision",
        schema=schema,
        debug_dump_dir=debug_dump_dir,
    )
    model_output = ImageOrientationDecisionModelOutput.model_validate(payload)
    return ImageOrientationDecision(
        doc_id=request.doc_id,
        source_filename=request.source_filename,
        page_number=request.page_number,
        model=config.model,
        rotation_degrees=model_output.rotation_degrees,
        is_already_upright=model_output.is_already_upright,
        needs_manual_review=model_output.needs_manual_review,
        confidence=model_output.confidence,
        reason=model_output.reason,
        visual_cues=model_output.visual_cues,
        prompt_version=config.prompt_version,
    )
