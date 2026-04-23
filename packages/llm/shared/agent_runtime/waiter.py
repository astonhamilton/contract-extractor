from __future__ import annotations

import time

from packages.data_store.connect import SqliteDb
from packages.data_store.llm_agent_runtime import queries
from packages.llm.shared.agent_runtime import store_mappers
from packages.llm.shared.agent_runtime.loop import AgentRuntimeLoop
from packages.llm.shared.agent_runtime.models import (
    AgentItem,
    AgentThread,
    AssistantTurn,
    ExecutionOptions,
)
from packages.schemas.common import BaseSchema


class WaitedTurnResult(BaseSchema):
    """Terminal turn result plus the new items produced after enqueue."""

    thread: AgentThread
    turn: AssistantTurn
    new_items: list[AgentItem]
    assistant_messages: list[str]


class WaitedThreadResult(BaseSchema):
    """Idle thread result plus the items produced since a baseline sequence."""

    thread: AgentThread
    turn: AssistantTurn | None = None
    new_items: list[AgentItem]
    assistant_messages: list[str]


def _thread_runtime(connection, thread_id: str) -> AgentThread:
    """Load one runtime thread or fail clearly when missing."""
    record = queries.get_thread(connection, thread_id)
    if record is None:
        raise ValueError(f"Unknown thread: {thread_id}")
    return store_mappers.thread_record_to_runtime(record)


def _turn_runtime(connection, turn_id: str) -> AssistantTurn:
    """Load one runtime turn or fail clearly when missing."""
    record = queries.get_turn(connection, turn_id)
    if record is None:
        raise ValueError(f"Unknown turn: {turn_id}")
    return store_mappers.turn_record_to_runtime(record)


def _thread_items(connection, thread_id: str) -> list[AgentItem]:
    """Load canonical runtime items for one thread."""
    return [
        store_mappers.item_record_to_runtime(record)
        for record in queries.list_items(connection, thread_id)
    ]


def _items_after_seq(items: list[AgentItem], baseline_seq: int) -> list[AgentItem]:
    """Return only items appended after one known sequence baseline."""
    return [item for item in items if (item.seq or 0) > baseline_seq]


def _assistant_messages(items: list[AgentItem]) -> list[str]:
    """Return assistant message texts from one item slice."""
    return [
        item.content_text
        for item in items
        if item.item_type == "message" and item.role == "assistant" and item.content_text
    ]


def _current_max_seq(connection, thread_id: str) -> int:
    """Return the latest persisted item sequence for one thread."""
    items = queries.list_items(connection, thread_id)
    return max((record.seq or 0) for record in items) if items else 0


def wait_for_turn(
    db: SqliteDb,
    turn_id: str,
    *,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.25,
    baseline_seq: int = 0,
) -> WaitedTurnResult:
    """Poll the DB until one turn reaches a terminal state or times out."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        with db.connect() as connection:
            turn = _turn_runtime(connection, turn_id)
            thread = _thread_runtime(connection, turn.thread_id)
            if turn.status in {"completed", "failed"} and turn.phase in {"completed", "failed"}:
                items = _thread_items(connection, thread.thread_id)
                new_items = _items_after_seq(items, baseline_seq)
                return WaitedTurnResult(
                    thread=thread,
                    turn=turn,
                    new_items=new_items,
                    assistant_messages=_assistant_messages(new_items),
                )
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Timed out waiting for turn: {turn_id}")
        time.sleep(poll_interval_seconds)


def wait_for_thread_idle(
    db: SqliteDb,
    thread_id: str,
    *,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.25,
    baseline_seq: int = 0,
) -> WaitedThreadResult:
    """Poll the DB until one thread becomes idle or times out."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        with db.connect() as connection:
            thread = _thread_runtime(connection, thread_id)
            if thread.active_turn_id is None and thread.phase == "idle":
                turn = None if thread.last_turn_id is None else _turn_runtime(connection, thread.last_turn_id)
                items = _thread_items(connection, thread.thread_id)
                new_items = _items_after_seq(items, baseline_seq)
                return WaitedThreadResult(
                    thread=thread,
                    turn=turn,
                    new_items=new_items,
                    assistant_messages=_assistant_messages(new_items),
                )
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Timed out waiting for thread idle: {thread_id}")
        time.sleep(poll_interval_seconds)


def start_thread_and_wait(
    db: SqliteDb,
    loop: AgentRuntimeLoop,
    *,
    agent_id: str,
    initial_user_text: str,
    title: str | None = None,
    metadata: dict[str, object] | None = None,
    execution_options: ExecutionOptions | None = None,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.25,
) -> WaitedTurnResult:
    """Create a thread with one initial message and wait for the first turn."""
    thread, turn = loop.start_thread(
        db,
        agent_id=agent_id,
        title=title,
        metadata=metadata,
        initial_user_text=initial_user_text,
        execution_options=execution_options,
    )
    if turn is None:
        raise ValueError("start_thread_and_wait requires initial_user_text.")
    with db.connect() as connection:
        baseline_seq = _current_max_seq(connection, thread.thread_id)
    return wait_for_turn(
        db,
        turn.turn_id,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        baseline_seq=baseline_seq,
    )


def start_task_and_wait(
    db: SqliteDb,
    loop: AgentRuntimeLoop,
    *,
    agent_id: str,
    task_text: str,
    title: str | None = None,
    metadata: dict[str, object] | None = None,
    execution_options: ExecutionOptions | None = None,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.25,
) -> WaitedTurnResult:
    """Create a task thread and wait for its first turn to finish."""
    thread, turn = loop.start_task(
        db,
        agent_id=agent_id,
        task_text=task_text,
        title=title,
        metadata=metadata,
        execution_options=execution_options,
    )
    with db.connect() as connection:
        baseline_seq = _current_max_seq(connection, thread.thread_id)
    return wait_for_turn(
        db,
        turn.turn_id,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        baseline_seq=baseline_seq,
    )


def send_input_and_wait(
    db: SqliteDb,
    loop: AgentRuntimeLoop,
    *,
    thread_id: str,
    user_text: str,
    execution_options: ExecutionOptions | None = None,
    metadata: dict[str, object] | None = None,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.25,
) -> WaitedTurnResult:
    """Append one user message to an existing thread and wait for the turn."""
    turn = loop.send_input(
        db,
        thread_id,
        user_text,
        execution_options=execution_options,
        metadata=metadata,
    )
    with db.connect() as connection:
        baseline_seq = _current_max_seq(connection, thread_id)
    return wait_for_turn(
        db,
        turn.turn_id,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        baseline_seq=baseline_seq,
    )
