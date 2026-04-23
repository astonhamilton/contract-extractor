from __future__ import annotations

from packages.app_services.chat_assistant.models import (
    ModelCallsPage,
    ModelCallSummary,
    ThreadTurnsPage,
    ToolInvocationsPage,
    ToolInvocationSummary,
    TurnDetail,
    TurnSummary,
)
from packages.data_store.connect import SqliteDb
from packages.data_store.llm_agent_runtime.models import (
    AssistantTurnRecord,
    ModelCallRecord,
    ToolInvocationRecord,
)
from packages.data_store.llm_agent_runtime.queries.assistant_turns import (
    get_turn,
    list_turns_for_thread_page,
)
from packages.data_store.llm_agent_runtime.queries.model_calls import (
    list_model_calls_for_turn_page,
)
from packages.data_store.llm_agent_runtime.queries.tool_invocations import (
    list_tool_invocations_for_turn_page,
)
from packages.data_store.llm_agent_runtime.queries.threads import get_thread


def turn_summary_from_record(turn: AssistantTurnRecord) -> TurnSummary:
    """Return the admin-facing summary shape for one turn record."""
    return TurnSummary(
        turn_id=turn.turn_id,
        thread_id=turn.thread_id,
        agent_id=turn.agent_id,
        status=turn.status,
        phase=turn.phase,
        queued_at=turn.queued_at.isoformat(),
        started_at=turn.started_at.isoformat(),
        completed_at=None if turn.completed_at is None else turn.completed_at.isoformat(),
        provider=turn.execution_options.provider,
        model=turn.execution_options.model,
        claim_worker_id=turn.claim_worker_id,
        heartbeat_at=None if turn.heartbeat_at is None else turn.heartbeat_at.isoformat(),
    )


def turn_detail_from_record(turn: AssistantTurnRecord) -> TurnDetail:
    """Return the admin-facing detail shape for one turn record."""
    summary = turn_summary_from_record(turn)
    return TurnDetail(
        **summary.model_dump(),
        provider_response_id=turn.provider_response_id,
        provider_conversation_id=turn.provider_conversation_id,
        usage=turn.usage,
        error=turn.error,
        metadata=turn.metadata,
        execution_options=turn.execution_options.model_dump(mode="json"),
    )


def model_call_summary_from_record(model_call: ModelCallRecord) -> ModelCallSummary:
    """Return the admin-facing summary shape for one model-call record."""
    return ModelCallSummary(
        model_call_id=model_call.model_call_id,
        turn_id=model_call.turn_id,
        thread_id=model_call.thread_id,
        ordinal=model_call.ordinal,
        provider=model_call.provider,
        model=model_call.model,
        status=model_call.status,
        started_at=model_call.started_at.isoformat(),
        completed_at=(
            None if model_call.completed_at is None else model_call.completed_at.isoformat()
        ),
        worker_id=model_call.worker_id,
        heartbeat_at=(
            None if model_call.heartbeat_at is None else model_call.heartbeat_at.isoformat()
        ),
    )


def tool_invocation_summary_from_record(
    tool_invocation: ToolInvocationRecord,
) -> ToolInvocationSummary:
    """Return the admin-facing summary shape for one tool invocation record."""
    return ToolInvocationSummary(
        tool_invocation_id=tool_invocation.tool_invocation_id,
        turn_id=tool_invocation.turn_id,
        thread_id=tool_invocation.thread_id,
        model_call_id=tool_invocation.model_call_id,
        tool_name=tool_invocation.tool_name,
        status=tool_invocation.status,
        started_at=tool_invocation.started_at.isoformat(),
        completed_at=(
            None
            if tool_invocation.completed_at is None
            else tool_invocation.completed_at.isoformat()
        ),
        worker_id=tool_invocation.worker_id,
        heartbeat_at=(
            None
            if tool_invocation.heartbeat_at is None
            else tool_invocation.heartbeat_at.isoformat()
        ),
        error_text=tool_invocation.error_text,
    )


def get_thread_turns(
    db: SqliteDb,
    *,
    thread_id: str,
    page: int = 1,
    page_size: int = 25,
) -> ThreadTurnsPage | None:
    """Return paginated admin-facing turns for one thread."""
    with db.connect() as connection:
        turn_records, total = list_turns_for_thread_page(
            connection,
            thread_id=thread_id,
            page=page,
            page_size=page_size,
        )
        if total == 0:
            if get_thread(connection, thread_id) is None:
                return None
        return ThreadTurnsPage(
            items=[turn_summary_from_record(turn) for turn in turn_records],
            total=total,
            page=max(page, 1),
            page_size=max(1, min(page_size, 100)),
        )


def get_turn_detail(db: SqliteDb, *, turn_id: str) -> TurnDetail | None:
    """Return the admin-facing detail record for one turn."""
    with db.connect() as connection:
        turn = get_turn(connection, turn_id)
        if turn is None:
            return None
        return turn_detail_from_record(turn)


def get_turn_model_calls(
    db: SqliteDb,
    *,
    turn_id: str,
    page: int = 1,
    page_size: int = 25,
) -> ModelCallsPage | None:
    """Return paginated admin-facing model calls for one turn."""
    with db.connect() as connection:
        turn = get_turn(connection, turn_id)
        if turn is None:
            return None
        model_calls, total = list_model_calls_for_turn_page(
            connection,
            turn_id=turn_id,
            page=page,
            page_size=page_size,
        )
        return ModelCallsPage(
            items=[model_call_summary_from_record(model_call) for model_call in model_calls],
            total=total,
            page=max(page, 1),
            page_size=max(1, min(page_size, 100)),
        )


def get_turn_tool_invocations(
    db: SqliteDb,
    *,
    turn_id: str,
    page: int = 1,
    page_size: int = 25,
) -> ToolInvocationsPage | None:
    """Return paginated admin-facing tool invocations for one turn."""
    with db.connect() as connection:
        turn = get_turn(connection, turn_id)
        if turn is None:
            return None
        tool_invocations, total = list_tool_invocations_for_turn_page(
            connection,
            turn_id=turn_id,
            page=page,
            page_size=page_size,
        )
        return ToolInvocationsPage(
            items=[
                tool_invocation_summary_from_record(tool_invocation)
                for tool_invocation in tool_invocations
            ],
            total=total,
            page=max(page, 1),
            page_size=max(1, min(page_size, 100)),
        )
