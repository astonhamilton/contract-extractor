from __future__ import annotations

from fastapi import Depends, HTTPException

from apps.api.deps import get_agent_runtime_db
from apps.api.routes.turn_detail.schema import TurnDetailResponse
from packages.app_services.chat_assistant.turns import get_turn_detail
from packages.data_store.connect import SqliteDb


def turn_detail(
    turn_id: str,
    db: SqliteDb = Depends(get_agent_runtime_db),
) -> TurnDetailResponse:
    """Return one admin-facing assistant turn."""

    detail = get_turn_detail(db, turn_id=turn_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Turn not found")
    return TurnDetailResponse(**detail.model_dump())
