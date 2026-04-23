from __future__ import annotations

from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.models import ToolCallRequest, ToolCallResult
from packages.llm.shared.agent_runtime.tools import ToolExecutionContext


def require_db(
    context: ToolExecutionContext,
    request: ToolCallRequest,
) -> tuple[SqliteDb, ToolCallResult | None]:
    """Return the configured DB or a failed tool result when unavailable."""
    if context.db is None:
        return None, ToolCallResult(
            tool_name=request.tool_name,
            status="failed",
            error_text="Tool execution context is missing a database handle.",
        )
    return context.db, None


def tool_error(request: ToolCallRequest, error_text: str) -> ToolCallResult:
    """Return a canonical failed tool result."""
    return ToolCallResult(
        tool_name=request.tool_name,
        status="failed",
        error_text=error_text,
    )
