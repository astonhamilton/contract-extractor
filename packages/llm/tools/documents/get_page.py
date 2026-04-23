from __future__ import annotations

from packages.app_services.corpus.pages import get_corpus_document_page_detail
from packages.llm.shared.agent_runtime.models import AgentToolDefinition, ToolCallRequest, ToolCallResult
from packages.llm.shared.agent_runtime.tools import ToolExecutionContext, ToolRegistry
from packages.llm.tools._helpers import require_db, tool_error
from packages.schemas.common import BaseSchema


class GetPageArgs(BaseSchema):
    """Arguments for one page lookup."""

    doc_id: str
    page_number: int


def _definition() -> AgentToolDefinition:
    schema = GetPageArgs.model_json_schema()
    return AgentToolDefinition(
        name="get_page",
        description=(
            "Return one specific document page using the best available content representation. "
            "Use this when you know the exact page you need for evidence."
        ),
        input_json_schema=schema,
    )


def _handler(context: ToolExecutionContext, request: ToolCallRequest) -> ToolCallResult:
    db, error = require_db(context, request)
    if error is not None:
        return error
    try:
        args = GetPageArgs.model_validate(request.arguments or {})
    except Exception as exc:  # noqa: BLE001
        return tool_error(request, f"Invalid arguments: {exc}")
    detail = get_corpus_document_page_detail(
        db,
        doc_id=args.doc_id,
        page_number=args.page_number,
        include_variants=False,
    )
    return ToolCallResult(
        tool_name=request.tool_name,
        result={
            "found": detail is not None,
            "page": None if detail is None else detail.model_dump(mode="json"),
        },
    )


def register_get_page_tool(registry: ToolRegistry) -> None:
    """Register the single-page retrieval tool."""
    registry.register(_definition(), _handler)
