from __future__ import annotations

import sqlite3
from datetime import datetime

from packages.data_store.connect import sqlite_transaction
from packages.data_store.llm_agent_runtime.common import turn_from_row
from packages.data_store.llm_agent_runtime.commands.threads import update_thread
from packages.data_store.llm_agent_runtime.common import dumps_json
from packages.data_store.llm_agent_runtime.models import AssistantTurnRecord, ThreadRecord


def create_turn(
    connection: sqlite3.Connection,
    turn: AssistantTurnRecord,
) -> AssistantTurnRecord:
    """Insert one assistant turn row."""
    connection.execute(
        """
        INSERT INTO asst_turns (
            turn_id, thread_id, agent_id, execution_options_json, status, phase,
            usage_json, error_json, provider_response_id, provider_conversation_id,
            claim_worker_id, heartbeat_at,
            metadata_json, queued_at, started_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            turn.turn_id,
            turn.thread_id,
            turn.agent_id,
            dumps_json(turn.execution_options.model_dump(mode="json")),
            turn.status,
            turn.phase,
            dumps_json(turn.usage),
            dumps_json(turn.error),
            turn.provider_response_id,
            turn.provider_conversation_id,
            turn.claim_worker_id,
            turn.heartbeat_at.isoformat() if turn.heartbeat_at else None,
            dumps_json(turn.metadata),
            turn.queued_at.isoformat(),
            turn.started_at.isoformat(),
            turn.completed_at.isoformat() if turn.completed_at else None,
        ),
    )
    return turn


def update_turn(
    connection: sqlite3.Connection,
    turn: AssistantTurnRecord,
) -> AssistantTurnRecord:
    """Update one assistant turn row."""
    connection.execute(
        """
        UPDATE asst_turns
        SET agent_id = ?, execution_options_json = ?, status = ?, phase = ?,
            usage_json = ?, error_json = ?, provider_response_id = ?,
            provider_conversation_id = ?, claim_worker_id = ?, heartbeat_at = ?, metadata_json = ?, queued_at = ?,
            started_at = ?, completed_at = ?
        WHERE turn_id = ?
        """,
        (
            turn.agent_id,
            dumps_json(turn.execution_options.model_dump(mode="json")),
            turn.status,
            turn.phase,
            dumps_json(turn.usage),
            dumps_json(turn.error),
            turn.provider_response_id,
            turn.provider_conversation_id,
            turn.claim_worker_id,
            turn.heartbeat_at.isoformat() if turn.heartbeat_at else None,
            dumps_json(turn.metadata),
            turn.queued_at.isoformat(),
            turn.started_at.isoformat(),
            turn.completed_at.isoformat() if turn.completed_at else None,
            turn.turn_id,
        ),
    )
    return turn


def claim_turn(
    connection: sqlite3.Connection,
    turn: AssistantTurnRecord,
    *,
    worker_id: str,
    heartbeat_at: datetime,
    stale_before: datetime,
) -> AssistantTurnRecord | None:
    """Claim one runnable assistant turn for one worker."""
    with sqlite_transaction(connection):
        row = connection.execute(
            """
            UPDATE asst_turns
            SET claim_worker_id = ?, heartbeat_at = ?
            WHERE turn_id = ?
              AND status IN ('queued', 'active')
              AND (
                claim_worker_id IS NULL
                OR claim_worker_id = ?
                OR (heartbeat_at IS NOT NULL AND heartbeat_at < ?)
              )
            RETURNING *
            """,
            (
                worker_id,
                heartbeat_at.isoformat(),
                turn.turn_id,
                worker_id,
                stale_before.isoformat(),
            ),
        ).fetchone()
        return None if row is None else turn_from_row(row)


def claim_next_runnable_turn(
    connection: sqlite3.Connection,
    *,
    worker_id: str,
    heartbeat_at: datetime,
    stale_before: datetime,
    thread_id: str | None = None,
) -> AssistantTurnRecord | None:
    """Atomically select and claim the next runnable assistant turn for one worker."""
    with sqlite_transaction(connection):
        sql = """
            WITH candidate AS (
                SELECT turn_id
                FROM asst_turns
                WHERE status IN ('queued', 'active')
                  AND (
                    claim_worker_id IS NULL
                    OR claim_worker_id = ?
                    OR (
                      heartbeat_at IS NOT NULL
                      AND heartbeat_at < ?
                      AND (
                        phase NOT IN ('executing_model', 'executing_tools')
                        OR (
                          phase = 'executing_model'
                          AND NOT EXISTS (
                            SELECT 1
                            FROM asst_model_calls mc
                            WHERE mc.turn_id = asst_turns.turn_id
                              AND mc.status = 'running'
                              AND mc.heartbeat_at IS NOT NULL
                              AND mc.heartbeat_at >= ?
                          )
                        )
                        OR (
                          phase = 'executing_tools'
                          AND NOT EXISTS (
                            SELECT 1
                            FROM asst_tool_invocations ti
                            WHERE ti.turn_id = asst_turns.turn_id
                              AND ti.status = 'running'
                              AND ti.heartbeat_at IS NOT NULL
                              AND ti.heartbeat_at >= ?
                          )
                        )
                      )
                    )
                  )
        """
        params: list[object] = [
            worker_id,
            stale_before.isoformat(),
            stale_before.isoformat(),
            stale_before.isoformat(),
        ]
        if thread_id:
            sql += " AND thread_id = ?"
            params.append(thread_id)
        sql += """
                ORDER BY queued_at, started_at
                LIMIT 1
            )
            UPDATE asst_turns
            SET claim_worker_id = ?, heartbeat_at = ?
            WHERE turn_id = (SELECT turn_id FROM candidate)
              AND status IN ('queued', 'active')
              AND (
                claim_worker_id IS NULL
                OR claim_worker_id = ?
                OR (
                  heartbeat_at IS NOT NULL
                  AND heartbeat_at < ?
                  AND (
                    phase NOT IN ('executing_model', 'executing_tools')
                    OR (
                      phase = 'executing_model'
                      AND NOT EXISTS (
                        SELECT 1
                        FROM asst_model_calls mc
                        WHERE mc.turn_id = asst_turns.turn_id
                          AND mc.status = 'running'
                          AND mc.heartbeat_at IS NOT NULL
                          AND mc.heartbeat_at >= ?
                      )
                    )
                    OR (
                      phase = 'executing_tools'
                      AND NOT EXISTS (
                        SELECT 1
                        FROM asst_tool_invocations ti
                        WHERE ti.turn_id = asst_turns.turn_id
                          AND ti.status = 'running'
                          AND ti.heartbeat_at IS NOT NULL
                          AND ti.heartbeat_at >= ?
                      )
                    )
                  )
                )
              )
            RETURNING *
        """
        params.extend(
            [
                worker_id,
                heartbeat_at.isoformat(),
                worker_id,
                stale_before.isoformat(),
                stale_before.isoformat(),
                stale_before.isoformat(),
            ]
        )
        row = connection.execute(sql, tuple(params)).fetchone()
        return None if row is None else turn_from_row(row)


def update_turn_heartbeat(
    connection: sqlite3.Connection,
    *,
    turn_id: str,
    worker_id: str,
    heartbeat_at: datetime,
) -> None:
    """Refresh the heartbeat for one claimed assistant turn."""
    connection.execute(
        """
        UPDATE asst_turns
        SET heartbeat_at = ?
        WHERE turn_id = ?
          AND claim_worker_id = ?
        """,
        (
            heartbeat_at.isoformat(),
            turn_id,
            worker_id,
        ),
    )


def recover_stale_turn_claims(
    connection: sqlite3.Connection,
    *,
    stale_before: datetime,
) -> list[str]:
    """Release stale turn claims when no fresher in-flight sub-action is still alive."""
    rows = connection.execute(
        """
        SELECT turn_id, phase
        FROM asst_turns
        WHERE status IN ('queued', 'active')
          AND claim_worker_id IS NOT NULL
          AND heartbeat_at IS NOT NULL
          AND heartbeat_at < ?
        ORDER BY queued_at, started_at
        """,
        (stale_before.isoformat(),),
    ).fetchall()
    recovered: list[str] = []
    for row in rows:
        turn_id = str(row["turn_id"])
        phase = str(row["phase"])
        if phase == "executing_model":
            model_row = connection.execute(
                """
                SELECT status, heartbeat_at
                FROM asst_model_calls
                WHERE turn_id = ?
                ORDER BY ordinal DESC
                LIMIT 1
                """,
                (turn_id,),
            ).fetchone()
            if (
                model_row is not None
                and str(model_row["status"]) == "running"
                and model_row["heartbeat_at"] is not None
                and datetime.fromisoformat(str(model_row["heartbeat_at"])) >= stale_before
            ):
                continue
        elif phase == "executing_tools":
            active_tool_row = connection.execute(
                """
                SELECT 1
                FROM asst_tool_invocations
                WHERE turn_id = ?
                  AND status = 'running'
                  AND heartbeat_at IS NOT NULL
                  AND heartbeat_at >= ?
                LIMIT 1
                """,
                (turn_id, stale_before.isoformat()),
            ).fetchone()
            if active_tool_row is not None:
                continue

        with sqlite_transaction(connection):
            recovered_row = connection.execute(
                """
                UPDATE asst_turns
                SET claim_worker_id = NULL,
                    heartbeat_at = NULL
                WHERE turn_id = ?
                  AND claim_worker_id IS NOT NULL
                  AND heartbeat_at IS NOT NULL
                  AND heartbeat_at < ?
                RETURNING turn_id
                """,
                (turn_id, stale_before.isoformat()),
            ).fetchone()
        if recovered_row is not None:
            recovered.append(str(recovered_row["turn_id"]))
    return recovered


def begin_turn_context(
    connection: sqlite3.Connection,
    *,
    thread: ThreadRecord,
    turn: AssistantTurnRecord,
) -> tuple[ThreadRecord, AssistantTurnRecord]:
    """Atomically move thread and turn from created into assembling_context."""
    with sqlite_transaction(connection):
        update_thread(connection, thread)
        update_turn(connection, turn)
        return thread, turn


def finalize_turn_completed(
    connection: sqlite3.Connection,
    *,
    thread: ThreadRecord,
    turn: AssistantTurnRecord,
) -> tuple[ThreadRecord, AssistantTurnRecord]:
    """Atomically finalize a completed turn and clear thread active state."""
    with sqlite_transaction(connection):
        update_thread(connection, thread)
        update_turn(connection, turn)
        return thread, turn


def finalize_turn_failed(
    connection: sqlite3.Connection,
    *,
    thread: ThreadRecord,
    turn: AssistantTurnRecord,
) -> tuple[ThreadRecord, AssistantTurnRecord]:
    """Atomically finalize a failed turn and clear thread active state."""
    with sqlite_transaction(connection):
        update_thread(connection, thread)
        update_turn(connection, turn)
        return thread, turn
