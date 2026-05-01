from __future__ import annotations

import sqlite3

from packages.data_store.llm_agent_runtime.common import dumps_json, thread_from_row
from packages.data_store.llm_agent_runtime.models import ThreadRecord
from packages.schemas.common import utc_now


def create_thread(connection: sqlite3.Connection, thread: ThreadRecord) -> ThreadRecord:
    """Insert one assistant thread row."""
    connection.execute(
        """
        INSERT INTO agent_runtime_threads (
            thread_id, agent_id, status, phase, active_turn_id, last_turn_id,
            execution_options_json, provider_continuations_json,
            metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            thread.thread_id,
            thread.agent_id,
            thread.status,
            thread.phase,
            thread.active_turn_id,
            thread.last_turn_id,
            dumps_json(thread.execution_options.model_dump(mode="json")),
            dumps_json(thread.provider_continuations),
            dumps_json(thread.metadata),
            thread.created_at.isoformat(),
            thread.updated_at.isoformat(),
        ),
    )
    return thread


def update_thread(connection: sqlite3.Connection, thread: ThreadRecord) -> ThreadRecord:
    """Update one assistant thread row."""
    thread = thread.model_copy(update={"updated_at": utc_now()})
    connection.execute(
        """
        UPDATE agent_runtime_threads
        SET agent_id = ?, status = ?, phase = ?, active_turn_id = ?, last_turn_id = ?,
            execution_options_json = ?, provider_continuations_json = ?,
            metadata_json = ?, updated_at = ?
        WHERE thread_id = ?
        """,
        (
            thread.agent_id,
            thread.status,
            thread.phase,
            thread.active_turn_id,
            thread.last_turn_id,
            dumps_json(thread.execution_options.model_dump(mode="json")),
            dumps_json(thread.provider_continuations),
            dumps_json(thread.metadata),
            thread.updated_at.isoformat(),
            thread.thread_id,
        ),
    )
    return thread


def delete_thread(connection: sqlite3.Connection, thread_id: str) -> bool:
    """Delete one assistant thread and dependent runtime rows."""

    cursor = connection.execute(
        "DELETE FROM agent_runtime_threads WHERE thread_id = ?",
        (thread_id,),
    )
    return cursor.rowcount > 0


def activate_thread_for_new_turn(
    connection: sqlite3.Connection,
    *,
    thread_id: str,
    turn_id: str,
    status: str = "running",
    phase: str = "created",
) -> ThreadRecord | None:
    """Atomically attach one newly enqueued turn only when the thread is idle."""
    now = utc_now().isoformat()
    row = connection.execute(
        """
        UPDATE agent_runtime_threads
        SET active_turn_id = ?, status = ?, phase = ?, updated_at = ?
        WHERE thread_id = ?
          AND active_turn_id IS NULL
        RETURNING *
        """,
        (turn_id, status, phase, now, thread_id),
    ).fetchone()
    return None if row is None else thread_from_row(row)


def recover_thread_to_turn(
    connection: sqlite3.Connection,
    *,
    thread_id: str,
    turn_id: str,
    status: str,
    phase: str,
) -> ThreadRecord | None:
    """Guardedly move thread bookkeeping back onto one specific turn."""
    now = utc_now().isoformat()
    row = connection.execute(
        """
        UPDATE agent_runtime_threads
        SET status = ?, phase = ?, active_turn_id = ?, updated_at = ?
        WHERE thread_id = ?
          AND (active_turn_id IS NULL OR active_turn_id = ?)
        RETURNING *
        """,
        (status, phase, turn_id, now, thread_id, turn_id),
    ).fetchone()
    return None if row is None else thread_from_row(row)
