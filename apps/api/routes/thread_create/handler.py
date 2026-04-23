from __future__ import annotations

from fastapi import Depends, HTTPException

from apps.api.deps import (
    get_agent_runtime_db,
    get_embedded_agent_runtime_service,
)
from apps.api.routes.thread_create.schema import (
    ThreadCreateRequest,
    ThreadCreateResponse,
    ThreadCreateThreadResponse,
    ThreadCreateTurnResponse,
)
from packages.app_services.chat_assistant.create_thread import create_thread
from packages.app_services.chat_assistant.models import ThreadInputItem
from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.embedded_service import EmbeddedAgentRuntimeService


def thread_create(
    request: ThreadCreateRequest,
    db: SqliteDb = Depends(get_agent_runtime_db),
    service: EmbeddedAgentRuntimeService = Depends(get_embedded_agent_runtime_service),
) -> ThreadCreateResponse:
    """Create one assistant conversation thread and optionally enqueue its first turn."""
    try:
        result = create_thread(
            db,
            service=service,
            title=request.title,
            items=[ThreadInputItem(**item.model_dump()) for item in request.items],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ThreadCreateResponse(
        thread=ThreadCreateThreadResponse(**result.thread.model_dump()),
        turn=(
            None
            if result.turn is None
            else ThreadCreateTurnResponse(**result.turn.model_dump())
        ),
    )
