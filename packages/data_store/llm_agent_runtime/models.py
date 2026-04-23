from __future__ import annotations

from datetime import datetime

from pydantic import Field

from packages.llm.shared.agent_runtime.models import ExecutionOptions
from packages.schemas.common import BaseSchema, utc_now


class ThreadRecord(BaseSchema):
    """DB exchange model for one assistant thread row."""

    thread_id: str
    thread_kind: str = "conversation"
    agent_id: str
    title: str | None = None
    status: str = "active"
    phase: str = "idle"
    active_turn_id: str | None = None
    last_turn_id: str | None = None
    execution_options: ExecutionOptions = Field(default_factory=ExecutionOptions)
    provider_continuations: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AssistantTurnRecord(BaseSchema):
    """DB exchange model for one assistant turn row."""

    turn_id: str
    thread_id: str
    agent_id: str
    execution_options: ExecutionOptions = Field(default_factory=ExecutionOptions)
    status: str = "queued"
    phase: str = "created"
    usage: dict[str, object] = Field(default_factory=dict)
    error: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)
    provider_response_id: str | None = None
    provider_conversation_id: str | None = None
    claim_worker_id: str | None = None
    heartbeat_at: datetime | None = None
    queued_at: datetime = Field(default_factory=utc_now)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class ModelCallRecord(BaseSchema):
    """DB exchange model for one model-call row."""

    model_call_id: str
    thread_id: str
    turn_id: str
    ordinal: int
    provider: str | None = None
    model: str | None = None
    status: str = "created"
    agent_spec_snapshot: dict[str, object] = Field(default_factory=dict)
    request_payload: dict[str, object] = Field(default_factory=dict)
    response_payload: dict[str, object] = Field(default_factory=dict)
    usage: dict[str, object] = Field(default_factory=dict)
    error: dict[str, object] = Field(default_factory=dict)
    provider_request_id: str | None = None
    provider_response_id: str | None = None
    worker_id: str | None = None
    heartbeat_at: datetime | None = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class ItemRecord(BaseSchema):
    """DB exchange model for one assistant item row."""

    item_id: str
    thread_id: str
    turn_id: str | None = None
    model_call_id: str | None = None
    parent_item_id: str | None = None
    seq: int | None = None
    item_type: str
    role: str | None = None
    content_text: str | None = None
    name: str | None = None
    arguments: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] = Field(default_factory=dict)
    provider_item_id: str | None = None
    provider_item_type: str | None = None
    provider_payload: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ToolInvocationRecord(BaseSchema):
    """DB exchange model for one tool-invocation row."""

    tool_invocation_id: str
    thread_id: str
    turn_id: str | None = None
    model_call_id: str | None = None
    tool_call_item_id: str | None = None
    tool_result_item_id: str | None = None
    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] = Field(default_factory=dict)
    status: str = "requested"
    error_text: str | None = None
    worker_id: str | None = None
    heartbeat_at: datetime | None = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
