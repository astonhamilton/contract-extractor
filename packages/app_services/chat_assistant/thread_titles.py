from __future__ import annotations

from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.embedded_service import EmbeddedAgentRuntimeService
from packages.llm.shared.agent_runtime.waiter import start_task_and_wait
from packages.llm.agents.app.thread_titling import build_title_request_prompt

_THREAD_TITLING_AGENT_ID = "thread_titling.v1"


def _clean_generated_title(text: str) -> str | None:
    """Return one usable generated title or None when empty."""
    cleaned = " ".join(text.replace("\n", " ").split()).strip().strip("\"' ")
    if not cleaned:
        return None
    return cleaned[:120]


def generate_thread_title(
    *,
    db: SqliteDb,
    service: EmbeddedAgentRuntimeService,
    source_text: str,
    timeout_seconds: float = 4.0,
    poll_interval_seconds: float = 0.05,
) -> str | None:
    """Best-effort synchronous title generation for one initial user message."""
    try:
        waited = start_task_and_wait(
            db,
            service.loop,
            agent_id=_THREAD_TITLING_AGENT_ID,
            task_text=build_title_request_prompt(source_text),
            title="Thread title generation",
            metadata={
                "task_type": "thread_title_generation",
                "source_text": source_text,
            },
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
    except Exception:
        return None
    generated = waited.assistant_messages[-1] if waited.assistant_messages else ""
    return _clean_generated_title(generated)
