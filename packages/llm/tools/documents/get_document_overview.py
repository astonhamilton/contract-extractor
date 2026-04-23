from __future__ import annotations

from packages.app_services.corpus.document_detail import get_corpus_document_detail
from packages.llm.shared.agent_runtime.models import AgentToolDefinition, ToolCallRequest, ToolCallResult
from packages.llm.shared.agent_runtime.tools import ToolExecutionContext, ToolRegistry
from packages.llm.tools._helpers import require_db, tool_error
from packages.schemas.common import BaseSchema


class GetDocumentOverviewArgs(BaseSchema):
    """Arguments for one document overview lookup."""

    doc_id: str


def _definition() -> AgentToolDefinition:
    schema = GetDocumentOverviewArgs.model_json_schema()
    return AgentToolDefinition(
        name="get_document_overview",
        description=(
            "Return one document's core shell: metadata, procurement context, classification, and overview. "
            "Use this when you have a candidate doc_id and want to quickly understand what the document is "
            "before reading notes or pages."
        ),
        input_json_schema=schema,
    )


def _handler(context: ToolExecutionContext, request: ToolCallRequest) -> ToolCallResult:
    db, error = require_db(context, request)
    if error is not None:
        return error
    try:
        args = GetDocumentOverviewArgs.model_validate(request.arguments or {})
    except Exception as exc:  # noqa: BLE001
        return tool_error(request, f"Invalid arguments: {exc}")
    detail = get_corpus_document_detail(db, doc_id=args.doc_id)
    return ToolCallResult(
        tool_name=request.tool_name,
        result={
            "found": detail is not None,
            "document": None if detail is None else detail.model_dump(mode="json"),
        },
    )


def register_get_document_overview_tool(registry: ToolRegistry) -> None:
    """Register the document-overview tool."""
    registry.register(_definition(), _handler)
