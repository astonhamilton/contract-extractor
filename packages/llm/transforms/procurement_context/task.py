from __future__ import annotations

import logging
from pathlib import Path

from packages.llm.transforms.procurement_context.coerce import coerce_procurement_context_payload
from packages.llm.transforms.procurement_context.config import ProcurementContextConfig
from packages.llm.transforms.procurement_context.prompt import procurement_context_system_prompt
from packages.llm.shared.task_runtime.content import read_optional_text
from packages.llm.shared.task_runtime.structured import completion_json_schema
from packages.llm.shared.strict_schema import enforce_openai_strict_required
from packages.schemas import (
    ProcurementContext,
    ProcurementContextInput,
    completed_procurement_context_status,
)


LOGGER = logging.getLogger(__name__)


def build_procurement_context_input(
    *,
    doc_id: str,
    source_filename: str,
    model: str,
    normalized_document_path: Path,
) -> ProcurementContextInput:
    """Build the typed input contract for one procurement-context request."""
    return ProcurementContextInput(
        doc_id=doc_id,
        source_filename=source_filename,
        model=model,
        normalized_document_path=str(normalized_document_path),
    )


def build_procurement_context_user_content(request: ProcurementContextInput) -> str:
    """Build the text payload for one procurement-context call."""
    normalized_text = read_optional_text(Path(request.normalized_document_path))
    if not normalized_text:
        raise FileNotFoundError(f"Normalized document input missing: {request.normalized_document_path}")

    return "\n".join(
        [
            "Infer procurement context from this normalized document representation.",
            f"doc_id: {request.doc_id}",
            f"source_filename: {request.source_filename}",
            "",
            "Normalized document XML:",
            normalized_text,
        ]
    )


def run_procurement_context(
    request: ProcurementContextInput,
    config: ProcurementContextConfig,
) -> ProcurementContext:
    """Run one procurement-context inference call and return a validated artifact."""
    LOGGER.info(
        "LLM procurement context | file=%s | input=%s",
        request.source_filename,
        request.normalized_document_path,
    )
    messages = [
        {"role": "system", "content": procurement_context_system_prompt()},
        {"role": "user", "content": build_procurement_context_user_content(request)},
    ]
    schema = enforce_openai_strict_required(ProcurementContext.model_json_schema())
    payload = completion_json_schema(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        schema_name="procurement_context",
        schema=schema,
    )
    payload = coerce_procurement_context_payload(payload)
    context = ProcurementContext.model_validate(payload).model_copy(
        update={"status": completed_procurement_context_status()}
    )
    LOGGER.info(
        "LLM procurement context complete | file=%s | procurement=%s | buyer=%s | seller=%s | confidence=%.2f",
        request.source_filename,
        context.is_procurement_doc,
        context.buyer,
        context.seller,
        context.confidence if context.confidence is not None else 0.0,
    )
    return context
