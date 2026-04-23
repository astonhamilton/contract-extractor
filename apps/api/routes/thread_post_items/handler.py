from __future__ import annotations

from fastapi import Depends, HTTPException

from apps.api.deps import get_agent_runtime_db, get_embedded_agent_runtime_service
from apps.api.routes.thread_post_items.schema import (
    ThreadPostItemsRequest,
    ThreadPostItemsResponse,
    ThreadPostItemsThreadResponse,
    ThreadPostItemsTurnResponse,
)
from packages.app_services.chat_assistant.models import ThreadInputItem
from packages.app_services.chat_assistant.post_items import post_thread_items
from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.embedded_service import EmbeddedAgentRuntimeService


def thread_post_items(
    thread_id: str,
    request: ThreadPostItemsRequest,
    db: SqliteDb = Depends(get_agent_runtime_db),
    service: EmbeddedAgentRuntimeService = Depends(get_embedded_agent_runtime_service),
) -> ThreadPostItemsResponse:
    """Append supported user input items to a thread and enqueue a turn."""

    try:
        result = post_thread_items(
            db,
            service=service,
            thread_id=thread_id,
            items=[ThreadInputItem(**item.model_dump()) for item in request.items],
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Unknown thread:"):
            raise HTTPException(status_code=404, detail="Thread not found") from exc
        if message.startswith("Thread already has active turn:"):
            raise HTTPException(status_code=409, detail="Thread already has an active turn") from exc
        raise HTTPException(status_code=400, detail=message) from exc

    return ThreadPostItemsResponse(
        thread=ThreadPostItemsThreadResponse(**result.thread.model_dump()),
        turn=ThreadPostItemsTurnResponse(**result.turn.model_dump()),
    )
