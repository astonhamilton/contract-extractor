from __future__ import annotations

import sqlite3

from packages.data_store.llm_agent_runtime.common import model_call_from_row
from packages.data_store.llm_agent_runtime.models import ModelCallRecord


def get_model_call(
    connection: sqlite3.Connection,
    model_call_id: str,
) -> ModelCallRecord | None:
    """Fetch one model call by id."""
    row = connection.execute(
        "SELECT * FROM asst_model_calls WHERE model_call_id = ?",
        (model_call_id,),
    ).fetchone()
    return None if row is None else model_call_from_row(row)


def get_latest_model_call(
    connection: sqlite3.Connection,
    turn_id: str,
) -> ModelCallRecord | None:
    """Fetch the most recent model call for one assistant turn."""
    row = connection.execute(
        """
        SELECT *
        FROM asst_model_calls
        WHERE turn_id = ?
        ORDER BY ordinal DESC
        LIMIT 1
        """,
        (turn_id,),
    ).fetchone()
    return None if row is None else model_call_from_row(row)


def list_model_calls_for_turn_page(
    connection: sqlite3.Connection,
    *,
    turn_id: str,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[ModelCallRecord], int]:
    """List paginated model calls for one turn."""
    bounded_page = max(page, 1)
    bounded_page_size = max(1, min(page_size, 100))
    count_row = connection.execute(
        "SELECT COUNT(*) AS count FROM asst_model_calls WHERE turn_id = ?",
        (turn_id,),
    ).fetchone()
    total = int(count_row["count"] or 0) if count_row is not None else 0
    offset = (bounded_page - 1) * bounded_page_size
    rows = connection.execute(
        """
        SELECT *
        FROM asst_model_calls
        WHERE turn_id = ?
        ORDER BY ordinal DESC, started_at DESC, model_call_id DESC
        LIMIT ? OFFSET ?
        """,
        (turn_id, bounded_page_size, offset),
    ).fetchall()
    return [model_call_from_row(row) for row in rows], total
