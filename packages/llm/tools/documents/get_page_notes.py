from __future__ import annotations

from packages.app_services.corpus.page_notes import get_corpus_document_page_notes
from packages.llm.shared.agent_runtime.models import AgentToolDefinition, ToolCallRequest, ToolCallResult
from packages.llm.shared.agent_runtime.tools import ToolExecutionContext, ToolRegistry
from packages.llm.tools._helpers import require_db, tool_error
from packages.schemas.common import BaseSchema


class GetPageNotesArgs(BaseSchema):
    """Arguments for one document's page-note slice."""

    doc_id: str
    page: int = 1


def _definition() -> AgentToolDefinition:
    schema = GetPageNotesArgs.model_json_schema()
    return AgentToolDefinition(
        name="get_page_notes",
        description=(
            "Return page-level summary notes for one document. "
            "Use this for large or dense documents to find likely relevant pages before pulling raw page content. "
            "Use page to inspect notes in fixed-size slices."
        ),
        input_json_schema=schema,
    )


def _handler(context: ToolExecutionContext, request: ToolCallRequest) -> ToolCallResult:
    db, error = require_db(context, request)
    if error is not None:
        return error
    try:
        args = GetPageNotesArgs.model_validate(request.arguments or {})
    except Exception as exc:  # noqa: BLE001
        return tool_error(request, f"Invalid arguments: {exc}")
    notes_page = get_corpus_document_page_notes(
        db,
        doc_id=args.doc_id,
        page=args.page,
    )
    return ToolCallResult(
        tool_name=request.tool_name,
        result=notes_page.model_dump(mode="json"),
    )


def register_get_page_notes_tool(registry: ToolRegistry) -> None:
    """Register the page-notes tool."""
    registry.register(_definition(), _handler)
