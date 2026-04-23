from __future__ import annotations

import sqlite3

from packages.data_store.llm_agent_runtime.common import turn_from_row
from packages.data_store.llm_agent_runtime.models import AssistantTurnRecord


def get_turn(connection: sqlite3.Connection, turn_id: str) -> AssistantTurnRecord | None:
    """Fetch one assistant turn by id."""
    row = connection.execute(
        "SELECT * FROM asst_turns WHERE turn_id = ?",
        (turn_id,),
    ).fetchone()
    return None if row is None else turn_from_row(row)


def list_runnable_turns(
    connection: sqlite3.Connection,
    *,
    limit: int,
    thread_id: str | None = None,
) -> list[AssistantTurnRecord]:
    """List queued or active assistant turns ready for the worker."""
    sql = """
        SELECT *
        FROM asst_turns
        WHERE status IN ('queued', 'active')
    """
    params: list[object] = []
    if thread_id:
        sql += " AND thread_id = ?"
        params.append(thread_id)
    sql += " ORDER BY queued_at, started_at LIMIT ?"
    params.append(limit)
    rows = connection.execute(sql, tuple(params)).fetchall()
    return [turn_from_row(row) for row in rows]


def list_turns_for_thread(
    connection: sqlite3.Connection,
    thread_id: str,
) -> list[AssistantTurnRecord]:
    """List all assistant turns for one thread in queue/start order."""
    rows = connection.execute(
        """
        SELECT *
        FROM asst_turns
        WHERE thread_id = ?
        ORDER BY queued_at, started_at, turn_id
        """,
        (thread_id,),
    ).fetchall()
    return [turn_from_row(row) for row in rows]


def list_turns_for_thread_page(
    connection: sqlite3.Connection,
    *,
    thread_id: str,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[AssistantTurnRecord], int]:
    """List paginated assistant turns for one thread."""
    bounded_page = max(page, 1)
    bounded_page_size = max(1, min(page_size, 100))
    count_row = connection.execute(
        "SELECT COUNT(*) AS count FROM asst_turns WHERE thread_id = ?",
        (thread_id,),
    ).fetchone()
    total = int(count_row["count"] or 0) if count_row is not None else 0
    offset = (bounded_page - 1) * bounded_page_size
    rows = connection.execute(
        """
        SELECT *
        FROM asst_turns
        WHERE thread_id = ?
        ORDER BY queued_at DESC, started_at DESC, turn_id DESC
        LIMIT ? OFFSET ?
        """,
        (thread_id, bounded_page_size, offset),
    ).fetchall()
    return [turn_from_row(row) for row in rows], total
