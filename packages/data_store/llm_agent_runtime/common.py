from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from packages.data_store.llm_agent_runtime.models import (
    AssistantTurnRecord,
    ItemRecord,
    ModelCallRecord,
    ThreadRecord,
    ToolInvocationRecord,
)
from packages.llm.shared.agent_runtime.models import ExecutionOptions


def dumps_json(value: object) -> str:
    """Serialize DB JSON payloads with stable ASCII output."""
    return json.dumps(value, ensure_ascii=True)


def loads_json_dict(value: object) -> dict[str, object]:
    """Deserialize a JSON dict payload from SQLite text."""
    if not value:
        return {}
    parsed = json.loads(str(value))
    return parsed if isinstance(parsed, dict) else {}


def parse_datetime(value: object) -> datetime | None:
    """Parse an ISO datetime stored in SQLite."""
    if value is None:
        return None
    return datetime.fromisoformat(str(value))


def next_item_seq(connection: sqlite3.Connection, thread_id: str) -> int:
    """Return the next sequence number for thread items."""
    row = connection.execute(
        "SELECT COALESCE(MAX(seq), 0) AS max_seq FROM asst_items WHERE thread_id = ?",
        (thread_id,),
    ).fetchone()
    return int(row["max_seq"] or 0) + 1


def thread_from_row(row: sqlite3.Row) -> ThreadRecord:
    """Map one `asst_threads` row into the data-store thread model."""
    return ThreadRecord(
        thread_id=str(row["thread_id"]),
        thread_kind=str(row["thread_kind"]),
        agent_id=str(row["agent_id"]),
        title=row["title"],
        status=str(row["status"]),
        phase=str(row["phase"]),
        active_turn_id=row["active_turn_id"],
        last_turn_id=row["last_turn_id"],
        execution_options=ExecutionOptions.model_validate(
            loads_json_dict(row["execution_options_json"])
        ),
        provider_continuations=loads_json_dict(row["provider_continuations_json"]),
        metadata=loads_json_dict(row["metadata_json"]),
        created_at=parse_datetime(row["created_at"]) or datetime.now(),
        updated_at=parse_datetime(row["updated_at"]) or datetime.now(),
    )


def turn_from_row(row: sqlite3.Row) -> AssistantTurnRecord:
    """Map one `asst_turns` row into the data-store turn model."""
    return AssistantTurnRecord(
        turn_id=str(row["turn_id"]),
        thread_id=str(row["thread_id"]),
        agent_id=str(row["agent_id"]),
        execution_options=ExecutionOptions.model_validate(
            loads_json_dict(row["execution_options_json"])
        ),
        status=str(row["status"]),
        phase=str(row["phase"]),
        usage=loads_json_dict(row["usage_json"]),
        error=loads_json_dict(row["error_json"]),
        metadata=loads_json_dict(row["metadata_json"]),
        provider_response_id=row["provider_response_id"],
        provider_conversation_id=row["provider_conversation_id"],
        claim_worker_id=row["claim_worker_id"],
        heartbeat_at=parse_datetime(row["heartbeat_at"]),
        queued_at=parse_datetime(row["queued_at"]) or datetime.now(),
        started_at=parse_datetime(row["started_at"]) or datetime.now(),
        completed_at=parse_datetime(row["completed_at"]),
    )


def item_from_row(row: sqlite3.Row) -> ItemRecord:
    """Map one `asst_items` row into the data-store item model."""
    return ItemRecord(
        item_id=str(row["item_id"]),
        thread_id=str(row["thread_id"]),
        turn_id=row["turn_id"],
        model_call_id=row["model_call_id"],
        parent_item_id=row["parent_item_id"],
        seq=int(row["seq"]),
        item_type=str(row["item_type"]),
        role=row["role"],
        content_text=row["content_text"],
        name=row["name"],
        arguments=loads_json_dict(row["arguments_json"]),
        result=loads_json_dict(row["result_json"]),
        provider_item_id=row["provider_item_id"],
        provider_item_type=row["provider_item_type"],
        provider_payload=loads_json_dict(row["provider_payload_json"]),
        metadata=loads_json_dict(row["metadata_json"]),
        created_at=parse_datetime(row["created_at"]) or datetime.now(),
    )


def model_call_from_row(row: sqlite3.Row) -> ModelCallRecord:
    """Map one `asst_model_calls` row into the data-store model-call model."""
    return ModelCallRecord(
        model_call_id=str(row["model_call_id"]),
        thread_id=str(row["thread_id"]),
        turn_id=str(row["turn_id"]),
        ordinal=int(row["ordinal"]),
        provider=row["provider"],
        model=row["model"],
        status=str(row["status"]),
        agent_spec_snapshot=loads_json_dict(row["agent_spec_snapshot_json"]),
        request_payload=loads_json_dict(row["request_json"]),
        response_payload=loads_json_dict(row["response_json"]),
        usage=loads_json_dict(row["usage_json"]),
        error=loads_json_dict(row["error_json"]),
        provider_request_id=row["provider_request_id"],
        provider_response_id=row["provider_response_id"],
        worker_id=row["worker_id"],
        heartbeat_at=parse_datetime(row["heartbeat_at"]),
        started_at=parse_datetime(row["started_at"]) or datetime.now(),
        completed_at=parse_datetime(row["completed_at"]),
    )


def tool_invocation_from_row(row: sqlite3.Row) -> ToolInvocationRecord:
    """Map one `asst_tool_invocations` row into the data-store tool-invocation model."""
    return ToolInvocationRecord(
        tool_invocation_id=str(row["tool_invocation_id"]),
        thread_id=str(row["thread_id"]),
        turn_id=row["turn_id"],
        model_call_id=row["model_call_id"],
        tool_call_item_id=row["tool_call_item_id"],
        tool_result_item_id=row["tool_result_item_id"],
        tool_name=str(row["tool_name"]),
        arguments=loads_json_dict(row["arguments_json"]),
        result=loads_json_dict(row["result_json"]),
        status=str(row["status"]),
        error_text=row["error_text"],
        worker_id=row["worker_id"],
        heartbeat_at=parse_datetime(row["heartbeat_at"]),
        started_at=parse_datetime(row["started_at"]) or datetime.now(),
        completed_at=parse_datetime(row["completed_at"]),
    )
