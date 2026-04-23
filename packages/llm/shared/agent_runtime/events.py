from __future__ import annotations

from enum import StrEnum
from typing import TypeAlias
from datetime import datetime

from pydantic import Field

from packages.schemas.common import BaseSchema, utc_now


class RuntimeEventType(StrEnum):
    """Canonical event names emitted by the agent runtime."""

    THREAD_CREATED = "thread.created"
    THREAD_UPDATED = "thread.updated"
    TURN_ENQUEUED = "turn.enqueued"
    TURN_CLAIMED = "turn.claimed"
    TURN_PHASE_CHANGED = "turn.phase_changed"
    TURN_STALE_CLAIM_RECOVERED = "turn.stale_claim_recovered"
    TURN_COMPLETED = "turn.completed"
    TURN_FAILED = "turn.failed"
    MODEL_CALL_CREATED = "model_call.created"
    MODEL_CALL_STARTED = "model_call.started"
    MODEL_CALL_COMPLETED = "model_call.completed"
    MODEL_CALL_FAILED = "model_call.failed"
    TOOL_INVOCATION_STARTED = "tool_invocation.started"
    TOOL_INVOCATION_COMPLETED = "tool_invocation.completed"
    TOOL_INVOCATION_FAILED = "tool_invocation.failed"
    TOOL_INVOCATION_STALE_RETRIED = "tool_invocation.stale_retried"
    TOOL_INVOCATION_STALE_FAILED = "tool_invocation.stale_failed"
    WORKER_PASS_COMPLETED = "worker.pass_completed"
    WORKER_RUN_ONCE_COMPLETED = "worker.run_once_completed"


EventPayload: TypeAlias = dict[str, object]


class ThreadCreatedPayload(BaseSchema):
    """Payload for thread creation events."""

    thread_kind: str = "conversation"
    agent_id: str
    title: str | None = None
    initial_input: bool = False


class TurnEnqueuedPayload(BaseSchema):
    """Payload for turn enqueue events."""

    agent_id: str
    provider: str | None = None
    model: str | None = None


class TurnClaimedPayload(BaseSchema):
    """Payload for turn claim events."""

    worker_id: str
    phase: str
    status: str


class TurnPhaseChangedPayload(BaseSchema):
    """Payload for turn phase transition events."""

    phase: str
    status: str


class TurnTerminalPayload(BaseSchema):
    """Payload for turn terminal events."""

    status: str
    phase: str


class TurnFailedPayload(BaseSchema):
    """Payload for failed turn events."""

    status: str
    phase: str
    error: dict[str, object] = Field(default_factory=dict)


class ModelCallCreatedPayload(BaseSchema):
    """Payload for model-call creation events."""

    provider: str
    model: str
    ordinal: int


class ModelCallStartedPayload(BaseSchema):
    """Payload for model-call start events."""

    provider: str
    model: str


class ModelCallCompletedPayload(BaseSchema):
    """Payload for model-call completion events."""

    finish_reason: str | None = None
    tool_requests: int
    output_items: int


class ErrorPayload(BaseSchema):
    """Payload for failure events."""

    error: str


class ToolInvocationStartedPayload(BaseSchema):
    """Payload for tool start events."""

    tool_name: str


class ToolInvocationCompletedPayload(BaseSchema):
    """Payload for tool completion/failure events."""

    tool_name: str
    status: str
    error_text: str | None = None
    result_item_id: str | None = None


class ToolInvocationStalePayload(BaseSchema):
    """Payload for stale tool recovery events."""

    tool_name: str
    error: str | None = None


class WorkerPassPayload(BaseSchema):
    """Payload for worker pass summary events."""

    turns_seen: int = 0
    turns_completed: int = 0
    turns_failed: int = 0
    stale_turn_claims_recovered: int = 0
    stale_turns_recovered: int = 0
    stale_tool_invocations_retried: int = 0
    stale_tool_invocations_failed: int = 0
    steps_executed: int = 0


class WorkerRunOncePayload(BaseSchema):
    """Payload for outer worker pass completion events."""

    started_at: datetime
    finished_at: datetime
    pending_turns: WorkerPassPayload


class RuntimeEvent(BaseSchema):
    """One structured runtime telemetry event."""

    event_id: str
    event_type: RuntimeEventType
    occurred_at: datetime = Field(default_factory=utc_now)
    thread_id: str | None = None
    turn_id: str | None = None
    model_call_id: str | None = None
    tool_invocation_id: str | None = None
    worker_id: str | None = None
    payload: EventPayload = Field(default_factory=dict)


def payload_dict(payload: BaseSchema | dict[str, object] | None = None) -> EventPayload:
    """Normalize typed payloads into runtime event payload dictionaries."""
    if payload is None:
        return {}
    if isinstance(payload, BaseSchema):
        return payload.model_dump(mode="json")
    return payload
