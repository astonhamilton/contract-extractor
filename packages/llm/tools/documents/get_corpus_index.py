from __future__ import annotations

from packages.app_services.corpus.assistant_index import get_corpus_index
from packages.llm.shared.agent_runtime.models import AgentToolDefinition, ToolCallRequest, ToolCallResult
from packages.llm.shared.agent_runtime.tools import ToolExecutionContext, ToolRegistry
from packages.llm.tools._helpers import require_db, tool_error
from packages.schemas.common import BaseSchema


class GetCorpusIndexArgs(BaseSchema):
    """Arguments for fetching a lightweight corpus index slice."""
    pass


def _definition() -> AgentToolDefinition:
    schema = GetCorpusIndexArgs.model_json_schema()
    return AgentToolDefinition(
        name="get_corpus_index",
        description=(
            "Return the full lightweight corpus index for first-pass navigation. "
            "Use this when you need a broad map of the whole corpus and want to reason over candidate documents "
            "before opening document-level detail. If a useful corpus index is already present in conversation "
            "history, prefer reasoning from that earlier index instead of calling this again."
        ),
        input_json_schema=schema,
    )


def _handler(context: ToolExecutionContext, request: ToolCallRequest) -> ToolCallResult:
    db, error = require_db(context, request)
    if error is not None:
        return error
    try:
        args = GetCorpusIndexArgs.model_validate(request.arguments or {})
    except Exception as exc:  # noqa: BLE001
        return tool_error(request, f"Invalid arguments: {exc}")
    items = get_corpus_index(
        db,
    )
    return ToolCallResult(
        tool_name=request.tool_name,
        result={
            "items": [item.model_dump(mode="json") for item in items],
            "count": len(items),
        },
    )


def register_get_corpus_index_tool(registry: ToolRegistry) -> None:
    """Register the corpus-index tool."""
    registry.register(_definition(), _handler)
