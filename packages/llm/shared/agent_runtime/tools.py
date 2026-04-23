from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Callable

from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.models import (
    AgentToolDefinition,
    ToolCallRequest,
    ToolCallResult,
)

if TYPE_CHECKING:
    from packages.llm.shared.agent_runtime.loop import AgentRuntimeLoop


@dataclass
class ToolExecutionContext:
    """Shared dependency context exposed to runtime tool handlers."""

    db: SqliteDb | None = None
    repo_root: Path | None = None
    runtime_loop: AgentRuntimeLoop | None = None


ToolHandler = Callable[[ToolExecutionContext, ToolCallRequest], ToolCallResult]


class ToolRegistry:
    """Runtime tool registry with definitions and execution helpers."""

    def __init__(self) -> None:
        self._definitions: dict[str, AgentToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, definition: AgentToolDefinition, handler: ToolHandler) -> None:
        """Register one runtime tool."""
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler

    def definitions(self) -> list[AgentToolDefinition]:
        """Return all registered tool definitions in stable name order."""
        return [self._definitions[name] for name in sorted(self._definitions)]

    def get_definition(self, name: str) -> AgentToolDefinition | None:
        """Return one tool definition when present."""
        return self._definitions.get(name)

    def execute(self, context: ToolExecutionContext, request: ToolCallRequest) -> ToolCallResult:
        """Execute one tool request and return a canonical result."""
        handler = self._handlers.get(request.tool_name)
        if handler is None:
            return ToolCallResult(
                tool_name=request.tool_name,
                status="failed",
                error_text=f"Unknown tool: {request.tool_name}",
            )
        return handler(context, request)
