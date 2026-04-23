from __future__ import annotations

from packages.app_services.corpus.pages import get_corpus_document_page_detail
from packages.llm.shared.agent_runtime.models import AgentToolDefinition, ToolCallRequest, ToolCallResult
from packages.llm.shared.agent_runtime.tools import ToolExecutionContext, ToolRegistry
from packages.llm.tools._helpers import require_db, tool_error
from packages.schemas.common import BaseSchema


class GetPagesArgs(BaseSchema):
    """Arguments for a small batch page lookup."""

    doc_id: str
    page_numbers: list[int]


def _definition() -> AgentToolDefinition:
    schema = GetPagesArgs.model_json_schema()
    return AgentToolDefinition(
        name="get_pages",
        description=(
            "Return a small selected set of pages from one document for evidence gathering or comparison. "
            "Use this when the answer depends on a handful of known pages rather than one page. "
            "Keep page_numbers small and focused."
        ),
        input_json_schema=schema,
    )


def _handler(context: ToolExecutionContext, request: ToolCallRequest) -> ToolCallResult:
    db, error = require_db(context, request)
    if error is not None:
        return error
    try:
        args = GetPagesArgs.model_validate(request.arguments or {})
    except Exception as exc:  # noqa: BLE001
        return tool_error(request, f"Invalid arguments: {exc}")
    normalized_page_numbers = sorted({int(page_number) for page_number in args.page_numbers})
    if not normalized_page_numbers:
        return tool_error(request, "page_numbers must contain at least one page.")
    pages: list[dict[str, object]] = []
    for page_number in normalized_page_numbers:
        detail = get_corpus_document_page_detail(
            db,
            doc_id=args.doc_id,
            page_number=page_number,
            include_variants=False,
        )
        if detail is not None:
            pages.append(detail.model_dump(mode="json"))
    return ToolCallResult(
        tool_name=request.tool_name,
        result={
            "doc_id": args.doc_id,
            "requested_page_numbers": normalized_page_numbers,
            "pages": pages,
            "count": len(pages),
        },
    )


def register_get_pages_tool(registry: ToolRegistry) -> None:
    """Register the multi-page retrieval tool."""
    registry.register(_definition(), _handler)
