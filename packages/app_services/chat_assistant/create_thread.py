from __future__ import annotations

from packages.app_services.chat_assistant.models import (
    CreateThreadResult,
    EnqueuedTurnSummary,
    ThreadInputItem,
)
from packages.app_services.chat_assistant.thread_detail import thread_detail_from_record
from packages.data_store.connect import SqliteDb
from packages.data_store.llm_agent_runtime.queries.threads import get_thread
from packages.llm.shared.agent_runtime.embedded_service import EmbeddedAgentRuntimeService

_CORPUS_ASSISTANT_AGENT_ID = "corpus_assistant.v1"
_DEFAULT_THREAD_TITLE = "New thread"
_FALLBACK_TITLE_LIMIT = 80


def _explicit_title(title: str | None) -> str | None:
    cleaned = title.strip() if title else ""
    return cleaned or None


def _coerce_initial_user_text(items: list[ThreadInputItem]) -> str | None:
    """Return one supported initial text item or None when no items were supplied."""
    if not items:
        return None
    if len(items) != 1:
        raise ValueError("At most one initial input item is supported.")
    item = items[0]
    if item.type != "text":
        raise ValueError("Only initial input items of type 'text' are supported.")
    text = item.data.strip()
    if not text:
        raise ValueError("Initial input text cannot be empty.")
    return text


def _fallback_title_from_message(text: str | None) -> str | None:
    """Return a lightweight local title derived from the initial user message."""

    if not text:
        return None
    compact = " ".join(text.split()).strip()
    if not compact:
        return None
    if len(compact) <= _FALLBACK_TITLE_LIMIT:
        return compact
    return compact[: _FALLBACK_TITLE_LIMIT - 1].rstrip() + "..."


def create_thread(
    db: SqliteDb,
    *,
    service: EmbeddedAgentRuntimeService,
    title: str | None,
    items: list[ThreadInputItem],
) -> CreateThreadResult:
    """Create one conversation thread and optionally enqueue the first turn."""
    explicit_title = _explicit_title(title)
    initial_user_text = _coerce_initial_user_text(items)
    if explicit_title is None and initial_user_text is None:
        raise ValueError("Provide either a title or one initial text item.")

    initial_title = explicit_title or _fallback_title_from_message(initial_user_text) or _DEFAULT_THREAD_TITLE

    thread, turn = service.loop.start_thread(
        db,
        agent_id=_CORPUS_ASSISTANT_AGENT_ID,
        title=initial_title,
        initial_user_text=initial_user_text,
    )

    with db.connect() as connection:
        persisted_thread = get_thread(connection, thread.thread_id)
        if persisted_thread is None:
            raise ValueError(f"Unknown thread: {thread.thread_id}")

        return CreateThreadResult(
            thread=thread_detail_from_record(persisted_thread),
            turn=(
                None
                if turn is None
                else EnqueuedTurnSummary(
                    turn_id=turn.turn_id,
                    status=turn.status,
                    phase=turn.phase,
                )
            ),
        )
