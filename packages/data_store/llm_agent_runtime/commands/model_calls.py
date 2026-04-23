from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime

from packages.data_store.connect import sqlite_transaction
from packages.data_store.llm_agent_runtime.common import dumps_json, model_call_from_row
from packages.data_store.llm_agent_runtime.commands.assistant_turns import update_turn
from packages.data_store.llm_agent_runtime.commands.items import append_items
from packages.data_store.llm_agent_runtime.commands.threads import recover_thread_to_turn
from packages.data_store.llm_agent_runtime.commands.tool_invocations import (
    create_tool_invocations,
)
from packages.data_store.llm_agent_runtime.models import (
    AssistantTurnRecord,
    ItemRecord,
    ModelCallRecord,
    ToolInvocationRecord,
)
from packages.schemas.common import utc_now


class _StaleRecoveryConflictError(RuntimeError):
    """Raised when stale recovery loses a race and should roll back."""


def create_model_call(
    connection: sqlite3.Connection,
    model_call: ModelCallRecord,
) -> ModelCallRecord:
    """Insert one model-call row."""
    connection.execute(
        """
        INSERT INTO asst_model_calls (
            model_call_id, thread_id, turn_id, ordinal, provider, model, status,
            agent_spec_snapshot_json,
            request_json, response_json, usage_json, error_json,
            provider_request_id, provider_response_id, worker_id, heartbeat_at,
            started_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            model_call.model_call_id,
            model_call.thread_id,
            model_call.turn_id,
            model_call.ordinal,
            model_call.provider,
            model_call.model,
            model_call.status,
            dumps_json(model_call.agent_spec_snapshot),
            dumps_json(model_call.request_payload),
            dumps_json(model_call.response_payload),
            dumps_json(model_call.usage),
            dumps_json(model_call.error),
            model_call.provider_request_id,
            model_call.provider_response_id,
            model_call.worker_id,
            model_call.heartbeat_at.isoformat() if model_call.heartbeat_at else None,
            model_call.started_at.isoformat(),
            model_call.completed_at.isoformat() if model_call.completed_at else None,
        ),
    )
    return model_call


def begin_model_call(
    connection: sqlite3.Connection,
    *,
    turn: AssistantTurnRecord,
    model_call: ModelCallRecord,
) -> tuple[AssistantTurnRecord, ModelCallRecord]:
    """Atomically persist a new model-call request snapshot and advance the turn."""
    with sqlite_transaction(connection):
        create_model_call(connection, model_call)
        update_turn(connection, turn)
        return turn, model_call


def update_model_call(
    connection: sqlite3.Connection,
    model_call: ModelCallRecord,
) -> ModelCallRecord:
    """Update one model-call row."""
    connection.execute(
        """
        UPDATE asst_model_calls
        SET provider = ?, model = ?, status = ?, agent_spec_snapshot_json = ?, request_json = ?, response_json = ?,
            usage_json = ?, error_json = ?, provider_request_id = ?, provider_response_id = ?,
            worker_id = ?, heartbeat_at = ?, started_at = ?, completed_at = ?
        WHERE model_call_id = ?
        """,
        (
            model_call.provider,
            model_call.model,
            model_call.status,
            dumps_json(model_call.agent_spec_snapshot),
            dumps_json(model_call.request_payload),
            dumps_json(model_call.response_payload),
            dumps_json(model_call.usage),
            dumps_json(model_call.error),
            model_call.provider_request_id,
            model_call.provider_response_id,
            model_call.worker_id,
            model_call.heartbeat_at.isoformat() if model_call.heartbeat_at else None,
            model_call.started_at.isoformat(),
            model_call.completed_at.isoformat() if model_call.completed_at else None,
            model_call.model_call_id,
        ),
    )
    return model_call


def claim_model_call(
    connection: sqlite3.Connection,
    model_call: ModelCallRecord,
    *,
    worker_id: str,
    heartbeat_at: datetime,
    stale_before: datetime,
) -> ModelCallRecord | None:
    """Claim one model call into running with a durable heartbeat."""
    with sqlite_transaction(connection):
        row = connection.execute(
            """
            UPDATE asst_model_calls
            SET status = 'running',
                worker_id = ?,
                heartbeat_at = ?,
                started_at = ?
            WHERE model_call_id = ?
              AND (
                status = 'created'
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
                model_call.model_call_id,
                stale_before.isoformat(),
            ),
        ).fetchone()
        return None if row is None else model_call_from_row(row)


def update_model_call_heartbeat(
    connection: sqlite3.Connection,
    *,
    model_call_id: str,
    heartbeat_at: datetime,
) -> None:
    """Refresh one running model-call heartbeat timestamp."""
    connection.execute(
        """
        UPDATE asst_model_calls
        SET heartbeat_at = ?
        WHERE model_call_id = ?
          AND status = 'running'
        """,
        (heartbeat_at.isoformat(), model_call_id),
    )


def complete_model_call_success(
    connection: sqlite3.Connection,
    *,
    turn: AssistantTurnRecord,
    model_call: ModelCallRecord,
    output_items: Sequence[ItemRecord],
    tool_invocations: Sequence[ToolInvocationRecord],
) -> tuple[AssistantTurnRecord, ModelCallRecord, list[ItemRecord]]:
    """Atomically persist one successful model-call action block."""
    with sqlite_transaction(connection):
        persisted_items = append_items(connection, output_items)
        create_tool_invocations(connection, tool_invocations)
        update_model_call(connection, model_call)
        update_turn(connection, turn)
        return turn, model_call, persisted_items


def complete_model_call_failure(
    connection: sqlite3.Connection,
    *,
    turn: AssistantTurnRecord,
    model_call: ModelCallRecord,
) -> tuple[AssistantTurnRecord, ModelCallRecord]:
    """Atomically persist one failed model-call action block."""
    with sqlite_transaction(connection):
        update_model_call(connection, model_call)
        update_turn(connection, turn)
        return turn, model_call


def recover_stale_model_calls(
    connection: sqlite3.Connection,
    *,
    stale_before: datetime,
    error_message: str,
) -> list[str]:
    """Mark stale model calls failed and reset their turns back to context assembly."""
    rows = connection.execute(
        """
        SELECT mc.model_call_id, mc.turn_id, t.thread_id
        FROM asst_model_calls mc
        JOIN asst_turns t ON t.turn_id = mc.turn_id
        WHERE mc.status = 'running'
          AND mc.heartbeat_at IS NOT NULL
          AND mc.heartbeat_at < ?
          AND t.phase = 'executing_model'
          AND t.status = 'active'
        """,
        (stale_before.isoformat(),),
    ).fetchall()
    recovered_turn_ids: list[str] = []
    for row in rows:
        now = utc_now()
        model_call_id = str(row["model_call_id"])
        turn_id = str(row["turn_id"])
        thread_id = str(row["thread_id"])
        try:
            with sqlite_transaction(connection):
                recovered_model_row = connection.execute(
                    """
                    UPDATE asst_model_calls
                    SET status = 'failed',
                        error_json = ?,
                        heartbeat_at = NULL,
                        completed_at = ?
                    WHERE model_call_id = ?
                      AND status = 'running'
                      AND heartbeat_at IS NOT NULL
                      AND heartbeat_at < ?
                    RETURNING model_call_id
                    """,
                    (
                        dumps_json({"message": error_message}),
                        now.isoformat(),
                        model_call_id,
                        stale_before.isoformat(),
                    ),
                ).fetchone()
                if recovered_model_row is None:
                    raise _StaleRecoveryConflictError
                updated_turn = connection.execute(
                    """
                    UPDATE asst_turns
                    SET status = 'active',
                        phase = 'assembling_context',
                        error_json = ?
                    WHERE turn_id = ?
                      AND phase = 'executing_model'
                      AND status = 'active'
                    RETURNING turn_id
                    """,
                    (dumps_json({}), turn_id),
                ).fetchone()
                if updated_turn is None:
                    raise _StaleRecoveryConflictError
                updated_thread = recover_thread_to_turn(
                    connection,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    status="running",
                    phase="assembling_context",
                )
                if updated_thread is None:
                    raise _StaleRecoveryConflictError
        except _StaleRecoveryConflictError:
            continue
        recovered_turn_ids.append(turn_id)
    return recovered_turn_ids
