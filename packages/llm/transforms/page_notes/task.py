from __future__ import annotations

import logging

from packages.llm.transforms.page_notes.config import PageNotesConfig
from packages.llm.transforms.page_notes.prompt import page_notes_system_prompt
from packages.llm.shared.task_runtime.structured import completion_json_schema
from packages.llm.shared.strict_schema import enforce_openai_strict_required
from packages.schemas import (
    PageNote,
    PageNoteModelOutput,
    PageNotesInput,
)
from packages.schemas.common import ProcessingStatus, StageStatus


LOGGER = logging.getLogger(__name__)


def build_page_notes_input(
    *,
    doc_id: str,
    source_filename: str,
    model: str,
    normalized_document_path: str,
    page_number: int,
    page_text: str,
    page_representation: str | None,
    page_quality_flags: list[str],
) -> PageNotesInput:
    """Build the typed input contract for one page-notes request."""
    return PageNotesInput(
        doc_id=doc_id,
        source_filename=source_filename,
        model=model,
        normalized_document_path=normalized_document_path,
        page_number=page_number,
        page_text=page_text,
        page_representation=page_representation,
        page_quality_flags=page_quality_flags,
    )


def build_page_notes_user_content(request: PageNotesInput) -> str:
    """Build the text payload for one page-notes call."""
    quality_flags = ", ".join(request.page_quality_flags) if request.page_quality_flags else "-"
    return "\n".join(
        [
            "Write a page-local retrieval note for this one page.",
            f"doc_id: {request.doc_id}",
            f"source_filename: {request.source_filename}",
            f"page_number: {request.page_number}",
            f"page_representation: {request.page_representation or 'unknown'}",
            f"page_quality_flags: {quality_flags}",
            "",
            "Page content:",
            request.page_text,
        ]
    )


def completed_page_note_status() -> StageStatus:
    """Return a completed status block for validated page-note outputs."""
    return StageStatus(status=ProcessingStatus.COMPLETED)


def run_page_note(
    request: PageNotesInput,
    config: PageNotesConfig,
    *,
    debug_dump_dir: str | None = None,
) -> PageNote:
    """Run one page-note call and return a validated artifact."""
    LOGGER.info(
        "LLM page note | file=%s | page=%s",
        request.source_filename,
        request.page_number,
    )
    messages = [
        {"role": "system", "content": page_notes_system_prompt()},
        {"role": "user", "content": build_page_notes_user_content(request)},
    ]
    schema = enforce_openai_strict_required(PageNoteModelOutput.model_json_schema())
    payload = completion_json_schema(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        reasoning_effort=config.reasoning_effort,
        schema_name="page_note",
        schema=schema,
        debug_dump_dir=debug_dump_dir,
    )
    payload.pop("doc_id", None)
    payload.pop("source_filename", None)
    payload.pop("page_number", None)
    payload.pop("status", None)
    model_output = PageNoteModelOutput.model_validate(payload)
    return PageNote(
        doc_id=request.doc_id,
        source_filename=request.source_filename,
        page_number=request.page_number,
        page_role=model_output.page_role,
        summary=model_output.summary,
        key_terms=model_output.key_terms,
        relevance_tags=model_output.relevance_tags,
        warnings=model_output.warnings,
        status=completed_page_note_status(),
    )
