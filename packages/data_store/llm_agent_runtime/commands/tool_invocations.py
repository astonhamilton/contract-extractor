from __future__ import annotations

import sqlite3
from datetime import datetime
from collections.abc import Sequence

from packages.data_store.connect import sqlite_transaction
from packages.data_store.llm_agent_runtime.common import (
    dumps_json,
    thread_from_row,
    tool_invocation_from_row,
    turn_from_row,
)
from packages.data_store.llm_agent_runtime.commands.items import append_items
from packages.data_store.llm_agent_runtime.commands.threads import recover_thread_to_turn
from packages.data_store.llm_agent_runtime.models import (
    AssistantTurnRecord,
    ItemRecord,
    ThreadRecord,
    ToolInvocationRecord,
)
from packages.schemas.common import utc_now


class _StaleToolRecoveryConflictError(RuntimeError):
    """Raised when stale tool recovery loses a race and should roll back."""


def create_tool_invocations(
    connection: sqlite3.Connection,
    invocations: Sequence[ToolInvocationRecord],
) -> list[ToolInvocationRecord]:
    """Insert requested tool-invocation rows."""
    for invocation in invocations:
        connection.execute(
            """
            INSERT INTO agent_runtime_tool_invocations (
                tool_invocation_id, thread_id, turn_id, model_call_id, tool_call_item_id,
                tool_result_item_id, tool_name, arguments_json, result_json, status,
                error_text, worker_id, heartbeat_at, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invocation.tool_invocation_id,
                invocation.thread_id,
                invocation.turn_id,
                invocation.model_call_id,
                invocation.tool_call_item_id,
                invocation.tool_result_item_id,
                invocation.tool_name,
                dumps_json(invocation.arguments),
                dumps_json(invocation.result),
                invocation.status,
                invocation.error_text,
                invocation.worker_id,
                invocation.heartbeat_at.isoformat() if invocation.heartbeat_at else None,
                invocation.started_at.isoformat(),
                invocation.completed_at.isoformat() if invocation.completed_at else None,
            ),
        )
    return list(invocations)


def update_tool_invocation(
    connection: sqlite3.Connection,
    invocation: ToolInvocationRecord,
) -> ToolInvocationRecord:
    """Update one tool invocation row."""
    connection.execute(
        """
        UPDATE agent_runtime_tool_invocations
        SET model_call_id = ?, tool_call_item_id = ?, tool_result_item_id = ?, tool_name = ?,
            arguments_json = ?, result_json = ?, status = ?, error_text = ?,
            worker_id = ?, heartbeat_at = ?, started_at = ?, completed_at = ?
        WHERE tool_invocation_id = ?
        """,
        (
            invocation.model_call_id,
            invocation.tool_call_item_id,
            invocation.tool_result_item_id,
            invocation.tool_name,
            dumps_json(invocation.arguments),
            dumps_json(invocation.result),
            invocation.status,
            invocation.error_text,
            invocation.worker_id,
            invocation.heartbeat_at.isoformat() if invocation.heartbeat_at else None,
            invocation.started_at.isoformat(),
            invocation.completed_at.isoformat() if invocation.completed_at else None,
            invocation.tool_invocation_id,
        ),
    )
    return invocation


def claim_tool_invocation(
    connection: sqlite3.Connection,
    invocation: ToolInvocationRecord,
    *,
    worker_id: str,
    heartbeat_at: datetime,
    stale_before: datetime,
) -> ToolInvocationRecord | None:
    """Claim one tool invocation into running with a durable heartbeat."""
    with sqlite_transaction(connection):
        row = connection.execute(
            """
            UPDATE agent_runtime_tool_invocations
            SET status = 'running',
                worker_id = ?,
                heartbeat_at = ?,
                started_at = ?
            WHERE tool_invocation_id = ?
              AND (
                status = 'requested'
                OR (
                  status = 'running'
                  AND heartbeat_at IS NOT NULL
                  AND heartbeat_at < ?
                )
              )
            RETURNING *
            """,
            (
                worker_id,
                heartbeat_at.isoformat(),
                heartbeat_at.isoformat(),
                invocation.tool_invocation_id,
                stale_before.isoformat(),
            ),
        ).fetchone()
        return None if row is None else tool_invocation_from_row(row)


def update_tool_invocation_heartbeat(
    connection: sqlite3.Connection,
    *,
    tool_invocation_id: str,
    heartbeat_at: datetime,
) -> None:
    """Refresh one running tool invocation heartbeat timestamp."""
    connection.execute(
        """
        UPDATE agent_runtime_tool_invocations
        SET heartbeat_at = ?
        WHERE tool_invocation_id = ?
          AND status = 'running'
        """,
        (heartbeat_at.isoformat(), tool_invocation_id),
    )


def complete_tool_invocation(
    connection: sqlite3.Connection,
    *,
    invocation: ToolInvocationRecord,
    result_item: ItemRecord,
) -> tuple[ToolInvocationRecord, ItemRecord]:
    """Atomically persist one tool-result item and completed invocation row."""
    with sqlite_transaction(connection):
        persisted_item = append_items(connection, [result_item])[0]
        completed = invocation.model_copy(update={"tool_result_item_id": persisted_item.item_id})
        update_tool_invocation(connection, completed)
        return completed, persisted_item


def reset_stale_tool_invocation(
    connection: sqlite3.Connection,
    *,
    invocation: ToolInvocationRecord,
    stale_before: datetime,
) -> ToolInvocationRecord:
    """Reset one stale tool invocation back to requested for retry."""
    with sqlite_transaction(connection):
        row = connection.execute(
            """
            UPDATE agent_runtime_tool_invocations
            SET status = 'requested',
                worker_id = NULL,
                heartbeat_at = NULL,
                error_text = NULL,
                completed_at = NULL
            WHERE tool_invocation_id = ?
              AND status = 'running'
              AND heartbeat_at IS NOT NULL
              AND heartbeat_at < ?
            RETURNING *
            """,
            (
                invocation.tool_invocation_id,
                stale_before.isoformat(),
            ),
        ).fetchone()
        if row is None:
            raise _StaleToolRecoveryConflictError
        return tool_invocation_from_row(row)


def fail_stale_tool_invocation(
    connection: sqlite3.Connection,
    *,
    invocation: ToolInvocationRecord,
    error_text: str,
    stale_before: datetime,
) -> ToolInvocationRecord:
    """Mark one stale tool invocation failed without retry."""
    with sqlite_transaction(connection):
        row = connection.execute(
            """
            UPDATE agent_runtime_tool_invocations
            SET status = 'failed',
                error_text = ?,
                worker_id = NULL,
                heartbeat_at = NULL,
                completed_at = ?
            WHERE tool_invocation_id = ?
              AND status = 'running'
              AND heartbeat_at IS NOT NULL
              AND heartbeat_at < ?
            RETURNING *
            """,
            (
                error_text,
                utc_now().isoformat(),
                invocation.tool_invocation_id,
                stale_before.isoformat(),
            ),
        ).fetchone()
        if row is None:
            raise _StaleToolRecoveryConflictError
        return tool_invocation_from_row(row)


def fail_stale_tool_invocation_turn(
    connection: sqlite3.Connection,
    *,
    invocation: ToolInvocationRecord,
    thread: ThreadRecord,
    turn: AssistantTurnRecord,
    error_text: str,
    stale_before: datetime,
) -> tuple[ToolInvocationRecord, ThreadRecord, AssistantTurnRecord]:
    """Atomically fail one stale tool invocation and move its turn into failed."""
    now = utc_now()
    failed_invocation = invocation.model_copy(
        update={
            "status": "failed",
            "error_text": error_text,
            "worker_id": None,
            "heartbeat_at": None,
            "completed_at": now,
        }
    )
    failed_thread = thread.model_copy(
        update={
            "status": "running",
            "phase": "failed",
            "active_turn_id": turn.turn_id,
        }
    )
    failed_turn = turn.model_copy(
        update={
            "status": "active",
            "phase": "failed",
            "error": {
                "message": error_text,
                "tool_name": invocation.tool_name,
            },
        }
    )
    with sqlite_transaction(connection):
        recovered_invocation = connection.execute(
            """
            UPDATE agent_runtime_tool_invocations
            SET status = 'failed',
                error_text = ?,
                worker_id = NULL,
                heartbeat_at = NULL,
                completed_at = ?
            WHERE tool_invocation_id = ?
              AND status = 'running'
              AND heartbeat_at IS NOT NULL
              AND heartbeat_at < ?
            RETURNING *
            """,
            (
                error_text,
                now.isoformat(),
                invocation.tool_invocation_id,
                stale_before.isoformat(),
            ),
        ).fetchone()
        if recovered_invocation is None:
            raise _StaleToolRecoveryConflictError
        updated_thread = recover_thread_to_turn(
            connection,
            thread_id=failed_thread.thread_id,
            turn_id=failed_thread.active_turn_id or turn.turn_id,
            status=failed_thread.status,
            phase=failed_thread.phase,
        )
        updated_turn = connection.execute(
            """
            UPDATE agent_runtime_turns
            SET status = ?, phase = ?, error_json = ?, provider_response_id = ?, provider_conversation_id = ?,
                claim_worker_id = ?, heartbeat_at = ?, metadata_json = ?, queued_at = ?, started_at = ?, completed_at = ?,
                execution_options_json = ?, agent_id = ?
            WHERE turn_id = ?
              AND phase = 'executing_tools'
              AND status = 'active'
            RETURNING *
            """,
            (
                failed_turn.status,
                failed_turn.phase,
                dumps_json(failed_turn.error),
                failed_turn.provider_response_id,
                failed_turn.provider_conversation_id,
                failed_turn.claim_worker_id,
                failed_turn.heartbeat_at.isoformat() if failed_turn.heartbeat_at else None,
                dumps_json(failed_turn.metadata),
                failed_turn.queued_at.isoformat(),
                failed_turn.started_at.isoformat(),
                failed_turn.completed_at.isoformat() if failed_turn.completed_at else None,
                dumps_json(failed_turn.execution_options.model_dump(mode="json")),
                failed_turn.agent_id,
                failed_turn.turn_id,
            ),
        ).fetchone()
        if updated_thread is None or updated_turn is None:
            raise _StaleToolRecoveryConflictError
        return (
            tool_invocation_from_row(recovered_invocation),
            updated_thread,
            turn_from_row(updated_turn),
        )
