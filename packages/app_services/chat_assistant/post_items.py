from __future__ import annotations

from packages.app_services.chat_assistant.models import (
    EnqueuedTurnSummary,
    PostThreadItemsResult,
    ThreadInputItem,
)
from packages.app_services.chat_assistant.thread_detail import thread_detail_from_record
from packages.data_store.connect import SqliteDb
from packages.data_store.llm_agent_runtime.queries.threads import get_thread
from packages.llm.shared.agent_runtime.embedded_service import EmbeddedAgentRuntimeService


def _coerce_single_user_message(items: list[ThreadInputItem]) -> str:
    """Return the supported text payload for the current runtime input surface."""
    if len(items) != 1:
        raise ValueError("Exactly one input item is supported.")
    item = items[0]
    if item.type != "message":
        raise ValueError("Only input items of type 'message' are supported.")
    text = item.data.strip()
    if not text:
        raise ValueError("Input message cannot be empty.")
    return text


def post_thread_items(
    db: SqliteDb,
    *,
    service: EmbeddedAgentRuntimeService,
    thread_id: str,
    items: list[ThreadInputItem],
) -> PostThreadItemsResult:
    """Append supported input items to a thread and enqueue one assistant turn."""
    user_text = _coerce_single_user_message(items)
    turn = service.loop.send_input(db, thread_id, user_text)
    with db.connect() as connection:
        thread = get_thread(connection, thread_id)
        if thread is None:
            raise ValueError(f"Unknown thread: {thread_id}")
        return PostThreadItemsResult(
            thread=thread_detail_from_record(thread),
            turn=EnqueuedTurnSummary(
                turn_id=turn.turn_id,
                status=turn.status,
                phase=turn.phase,
            ),
        )
