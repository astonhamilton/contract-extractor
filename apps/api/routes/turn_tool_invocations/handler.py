from __future__ import annotations

from fastapi import Depends, HTTPException, Query

from apps.api.deps import get_agent_runtime_db
from apps.api.routes.turn_tool_invocations.schema import (
    ToolInvocationSummaryResponse,
    TurnToolInvocationsResponse,
)
from packages.app_services.chat_assistant.turns import get_turn_tool_invocations
from packages.data_store.connect import SqliteDb


def turn_tool_invocations(
    turn_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: SqliteDb = Depends(get_agent_runtime_db),
) -> TurnToolInvocationsResponse:
    """Return paginated tool invocations for one assistant turn."""

    result = get_turn_tool_invocations(
        db,
        turn_id=turn_id,
        page=page,
        page_size=page_size,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    return TurnToolInvocationsResponse(
        items=[
            ToolInvocationSummaryResponse(**item.model_dump())
            for item in result.items
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )
