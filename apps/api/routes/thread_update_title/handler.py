from __future__ import annotations

from fastapi import Depends, HTTPException

from apps.api.deps import get_agent_runtime_db, get_embedded_agent_runtime_event_bus
from apps.api.routes.thread_update_title.schema import (
    ThreadUpdateTitleRequest,
    ThreadUpdateTitleResponse,
)
from packages.app_services.chat_assistant.update_thread_title import update_thread_title
from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.event_bus import InMemoryRuntimeEventBus
from packages.llm.shared.agent_runtime.events import RuntimeEvent, RuntimeEventType
from packages.llm.shared.agent_runtime.models import new_id


def thread_update_title(
    thread_id: str,
    request: ThreadUpdateTitleRequest,
    db: SqliteDb = Depends(get_agent_runtime_db),
    bus: InMemoryRuntimeEventBus = Depends(get_embedded_agent_runtime_event_bus),
) -> ThreadUpdateTitleResponse:
    """Update one assistant thread title."""

    try:
        detail = update_thread_title(
            db,
            thread_id=thread_id,
            title=request.title,
        )
    except ValueError as exc:
        message = str(exc)
        if message.startswith("Unknown thread:"):
            raise HTTPException(status_code=404, detail="Thread not found") from exc
        raise HTTPException(status_code=400, detail=message) from exc

    bus.emit(
        RuntimeEvent(
            event_id=new_id("evt"),
            event_type=RuntimeEventType.THREAD_UPDATED,
            thread_id=thread_id,
            payload={"title": detail.title},
        )
    )
    return ThreadUpdateTitleResponse(**detail.model_dump())
