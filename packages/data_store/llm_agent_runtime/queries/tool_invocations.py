from __future__ import annotations

import sqlite3
from datetime import datetime

from packages.data_store.llm_agent_runtime.common import tool_invocation_from_row
from packages.data_store.llm_agent_runtime.models import ToolInvocationRecord


def get_tool_invocation(
    connection: sqlite3.Connection,
    tool_invocation_id: str,
) -> ToolInvocationRecord | None:
    """Fetch one tool invocation by id."""
    row = connection.execute(
        "SELECT * FROM agent_runtime_tool_invocations WHERE tool_invocation_id = ?",
        (tool_invocation_id,),
    ).fetchone()
    return None if row is None else tool_invocation_from_row(row)


def list_pending_tool_invocations(
    connection: sqlite3.Connection,
    turn_id: str,
) -> list[ToolInvocationRecord]:
    """List requested/running tool invocations for one assistant turn."""
    rows = connection.execute(
        """
        SELECT *
        FROM agent_runtime_tool_invocations
        WHERE turn_id = ?
          AND status IN ('requested', 'running')
        ORDER BY started_at, tool_invocation_id
        """,
        (turn_id,),
    ).fetchall()
    return [tool_invocation_from_row(row) for row in rows]


def list_stale_tool_invocations(
    connection: sqlite3.Connection,
    *,
    stale_before: datetime,
) -> list[ToolInvocationRecord]:
    """List running tool invocations whose heartbeat appears abandoned."""
    rows = connection.execute(
        """
        SELECT ti.*
        FROM agent_runtime_tool_invocations ti
        JOIN agent_runtime_turns t ON t.turn_id = ti.turn_id
        WHERE ti.status = 'running'
          AND ti.heartbeat_at IS NOT NULL
          AND ti.heartbeat_at < ?
          AND t.phase = 'executing_tools'
          AND t.status = 'active'
        ORDER BY ti.started_at, ti.tool_invocation_id
        """,
        (stale_before.isoformat(),),
    ).fetchall()
    return [tool_invocation_from_row(row) for row in rows]


def list_tool_invocations_for_turn_page(
    connection: sqlite3.Connection,
    *,
    turn_id: str,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[ToolInvocationRecord], int]:
    """List paginated tool invocations for one turn."""
    bounded_page = max(page, 1)
    bounded_page_size = max(1, min(page_size, 100))
    count_row = connection.execute(
        "SELECT COUNT(*) AS count FROM agent_runtime_tool_invocations WHERE turn_id = ?",
        (turn_id,),
    ).fetchone()
    total = int(count_row["count"] or 0) if count_row is not None else 0
    offset = (bounded_page - 1) * bounded_page_size
    rows = connection.execute(
        """
        SELECT *
        FROM agent_runtime_tool_invocations
        WHERE turn_id = ?
        ORDER BY started_at DESC, tool_invocation_id DESC
        LIMIT ? OFFSET ?
        """,
        (turn_id, bounded_page_size, offset),
    ).fetchall()
    return [tool_invocation_from_row(row) for row in rows], total
