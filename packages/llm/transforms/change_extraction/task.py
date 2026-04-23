from __future__ import annotations

import logging
from pathlib import Path

from packages.llm.transforms.change_extraction.coerce import coerce_change_extraction_payload
from packages.llm.transforms.change_extraction.config import ChangeExtractionConfig
from packages.llm.transforms.change_extraction.prompt import change_extraction_system_prompt
from packages.llm.shared.task_runtime.content import read_optional_text
from packages.llm.shared.task_runtime.structured import completion_json_schema
from packages.llm.shared.strict_schema import enforce_openai_strict_required
from packages.schemas import (
    ChangeExtraction,
    ChangeExtractionInput,
    ChangeKind,
    ChangeExtractionModelOutput,
    completed_change_extraction_status,
)


LOGGER = logging.getLogger(__name__)


def _write_debug_prompt_bundle(
    *,
    debug_dump_dir: Path,
    system_prompt: str,
    user_content: str,
) -> None:
    """Write the assembled prompt bundle for per-run debugging."""
    debug_dump_dir.mkdir(parents=True, exist_ok=True)
    (debug_dump_dir / "assembled_system_prompt.md").write_text(
        system_prompt + "\n",
        encoding="utf-8",
    )
    (debug_dump_dir / "user_content.txt").write_text(
        user_content + "\n",
        encoding="utf-8",
    )


def build_change_extraction_input(
    *,
    doc_id: str,
    source_filename: str,
    model: str,
    normalized_document_path: Path,
    classified_change_kind: ChangeKind,
) -> ChangeExtractionInput:
    """Build the typed input contract for one change extraction request."""
    return ChangeExtractionInput(
        doc_id=doc_id,
        source_filename=source_filename,
        model=model,
        normalized_document_path=str(normalized_document_path),
        classified_change_kind=classified_change_kind,
    )


def build_change_extraction_user_content(request: ChangeExtractionInput) -> str:
    """Build the text payload for one change extraction call."""
    normalized_text = read_optional_text(Path(request.normalized_document_path))
    if not normalized_text:
        raise FileNotFoundError(f"Normalized document input missing: {request.normalized_document_path}")

    return "\n".join(
        [
            "Extract contractual deltas from this normalized change document representation.",
            f"doc_id: {request.doc_id}",
            f"source_filename: {request.source_filename}",
            f"classified_change_kind: {request.classified_change_kind.value}",
            "",
            "Normalized document XML:",
            normalized_text,
        ]
    )


def run_change_extraction(
    request: ChangeExtractionInput,
    config: ChangeExtractionConfig,
    *,
    debug_dump_dir: Path | None = None,
) -> ChangeExtraction:
    """Run one change extraction call and return a validated artifact."""
    LOGGER.info(
        "LLM change extraction | file=%s | input=%s | classified_change_kind=%s",
        request.source_filename,
        request.normalized_document_path,
        request.classified_change_kind,
    )
    system_prompt = change_extraction_system_prompt()
    user_content = build_change_extraction_user_content(request)
    if debug_dump_dir is not None:
        _write_debug_prompt_bundle(
            debug_dump_dir=debug_dump_dir,
            system_prompt=system_prompt,
            user_content=user_content,
        )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    schema = enforce_openai_strict_required(ChangeExtractionModelOutput.model_json_schema())
    payload = completion_json_schema(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        reasoning_effort=config.reasoning_effort,
        schema_name="change_extraction",
        schema=schema,
        debug_dump_dir=str(debug_dump_dir) if debug_dump_dir is not None else None,
    )
    payload = coerce_change_extraction_payload(payload)
    payload.pop("doc_id", None)
    payload.pop("source_filename", None)
    payload.pop("status", None)
    model_output = ChangeExtractionModelOutput.model_validate(payload)
    extraction = ChangeExtraction(
        doc_id=request.doc_id,
        source_filename=request.source_filename,
        target_artifact=model_output.target_artifact,
        change=model_output.change,
        resulting_state=model_output.resulting_state,
        key_clauses=model_output.key_clauses,
        quality=model_output.quality,
        citations=model_output.citations,
        status=completed_change_extraction_status(),
    )
    LOGGER.info(
        "LLM change extraction complete | file=%s | target=%s | confidence=%.2f",
        request.source_filename,
        extraction.target_artifact.answer,
        extraction.extraction_confidence if extraction.extraction_confidence is not None else 0.0,
    )
    return extraction
