from __future__ import annotations

from packages.app_services.corpus.notes import get_corpus_document_notes
from packages.llm.shared.agent_runtime.models import AgentToolDefinition, ToolCallRequest, ToolCallResult
from packages.llm.shared.agent_runtime.tools import ToolExecutionContext, ToolRegistry
from packages.llm.tools._helpers import require_db, tool_error
from packages.schemas.common import BaseSchema


class GetDocumentNotesArgs(BaseSchema):
    """Arguments for one document-notes lookup."""

    doc_id: str


def _definition() -> AgentToolDefinition:
    schema = GetDocumentNotesArgs.model_json_schema()
    return AgentToolDefinition(
        name="get_document_notes",
        description=(
            "Return governing notes or change notes for one document, including citations where available. "
            "Use this before raw page retrieval to understand what the document governs or changes and to decide "
            "whether the document is relevant enough to inspect further."
        ),
        input_json_schema=schema,
    )


def _handler(context: ToolExecutionContext, request: ToolCallRequest) -> ToolCallResult:
    db, error = require_db(context, request)
    if error is not None:
        return error
    try:
        args = GetDocumentNotesArgs.model_validate(request.arguments or {})
    except Exception as exc:  # noqa: BLE001
        return tool_error(request, f"Invalid arguments: {exc}")
    notes = get_corpus_document_notes(db, doc_id=args.doc_id)
    return ToolCallResult(
        tool_name=request.tool_name,
        result={
            "found": notes is not None,
            "notes": None if notes is None else notes.model_dump(mode="json"),
        },
    )


def register_get_document_notes_tool(registry: ToolRegistry) -> None:
    """Register the document-notes tool."""
    registry.register(_definition(), _handler)
