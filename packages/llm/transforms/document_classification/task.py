from __future__ import annotations

import logging
from pathlib import Path

from packages.llm.transforms.document_classification.config import DocumentClassificationConfig
from packages.llm.transforms.document_classification.coerce import coerce_document_classification_payload
from packages.llm.transforms.document_classification.prompt import classification_system_prompt
from packages.llm.shared.task_runtime.content import read_optional_text
from packages.llm.shared.task_runtime.structured import completion_json_schema
from packages.llm.shared.strict_schema import enforce_openai_strict_required
from packages.schemas import (
    DocumentClassification,
    DocumentClassificationInput,
    completed_classification_status,
)


LOGGER = logging.getLogger(__name__)


def build_classification_input(
    *,
    doc_id: str,
    source_filename: str,
    model: str,
    normalized_document_path: Path,
) -> DocumentClassificationInput:
    """Build the typed input contract for one document classification request."""
    return DocumentClassificationInput(
        doc_id=doc_id,
        source_filename=source_filename,
        model=model,
        normalized_document_path=str(normalized_document_path),
    )


def build_classification_user_content(request: DocumentClassificationInput) -> str:
    """Build the text payload for document classification."""
    normalized_text = read_optional_text(Path(request.normalized_document_path))
    if not normalized_text:
        raise FileNotFoundError(f"Normalized document input missing: {request.normalized_document_path}")

    return "\n".join(
        [
            "Classify this contract-related document using the provided normalized document representation.",
            f"doc_id: {request.doc_id}",
            f"source_filename: {request.source_filename}",
            "",
            "Normalized document XML:",
            normalized_text,
        ]
    )


def run_document_classification(
    request: DocumentClassificationInput,
    config: DocumentClassificationConfig,
) -> DocumentClassification:
    """Run one document classification call and return a validated artifact."""
    LOGGER.info(
        "LLM document classification | file=%s | input=%s",
        request.source_filename,
        request.normalized_document_path,
    )
    messages = [
        {"role": "system", "content": classification_system_prompt()},
        {"role": "user", "content": build_classification_user_content(request)},
    ]
    schema = enforce_openai_strict_required(DocumentClassification.model_json_schema())
    payload = completion_json_schema(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        reasoning_effort=config.reasoning_effort,
        schema_name="document_classification",
        schema=schema,
    )
    payload = coerce_document_classification_payload(payload)
    classification = DocumentClassification.model_validate(payload).model_copy(
        update={"status": completed_classification_status()}
    )
    LOGGER.info(
        "LLM document classification complete | file=%s | stage=%s | role=%s | change_kind=%s | confidence=%.2f",
        request.source_filename,
        classification.procurement_stage,
        classification.document_role,
        classification.change_kind,
        classification.confidence,
    )
    return classification
