from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import Field

from packages.schemas.common import BaseSchema, utc_now


def new_id(prefix: str) -> str:
    """Return a compact opaque id for runtime entities."""
    return f"{prefix}_{uuid4().hex}"


class AgentToolDefinition(BaseSchema):
    """Declarative tool definition exposed to one assistant."""

    name: str
    description: str
    input_json_schema: dict[str, object] = Field(default_factory=dict)
    retry_on_stale: bool = True


class HostedToolDefinition(BaseSchema):
    """Declarative provider-hosted tool configuration for one assistant."""

    name: str
    provider: str | None = None
    config: dict[str, object] = Field(default_factory=dict)
    enabled: bool = True


class AgentSpec(BaseSchema):
    """Declarative definition of one assistant/agent."""

    agent_id: str
    instructions: str
    default_provider: str
    default_model: str
    local_tools: list[AgentToolDefinition] = Field(default_factory=list)
    hosted_tools: list[HostedToolDefinition] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExecutionOptions(BaseSchema):
    """Resolved or partially overridden execution options for one turn."""

    provider: str | None = None
    model: str | None = None
    continuity_mode: str | None = None
    provider_continuity: str | None = None
    provider_extras: dict[str, object] = Field(default_factory=dict)
    reasoning_effort: str | None = None


class AgentThread(BaseSchema):
    """Canonical assistant thread metadata independent of provider format."""

    thread_id: str = Field(default_factory=lambda: new_id("thread"))
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


class AssistantTurn(BaseSchema):
    """One durable assistant turn inside a thread."""

    turn_id: str = Field(default_factory=lambda: new_id("turn"))
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


class AgentModelCall(BaseSchema):
    """One model request/response round-trip inside an assistant turn."""

    model_call_id: str = Field(default_factory=lambda: new_id("mc"))
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


class AgentItem(BaseSchema):
    """Canonical persisted thread item."""

    item_id: str = Field(default_factory=lambda: new_id("item"))
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


class ToolCallRequest(BaseSchema):
    """Canonical runtime tool-call request."""

    tool_call_id: str = Field(default_factory=lambda: new_id("toolreq"))
    tool_name: str
    arguments: dict[str, object] = Field(default_factory=dict)
    provider_item_id: str | None = None
    item_id: str | None = None


class ToolCallResult(BaseSchema):
    """Canonical runtime tool-call result."""

    tool_name: str
    result: dict[str, object] = Field(default_factory=dict)
    status: str = "completed"
    error_text: str | None = None


class ToolInvocation(BaseSchema):
    """Durable execution record for one tool call."""

    tool_invocation_id: str = Field(default_factory=lambda: new_id("tool"))
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


class ModelInvocationRequest(BaseSchema):
    """Canonical executor request for one model round-trip."""

    thread_id: str
    turn_id: str
    model_call_id: str
    provider: str
    model: str
    instructions: str
    items: list[AgentItem] = Field(default_factory=list)
    local_tools: list[AgentToolDefinition] = Field(default_factory=list)
    hosted_tools: list[HostedToolDefinition] = Field(default_factory=list)
    continuity_mode: str = "stateless"
    continuation: dict[str, object] = Field(default_factory=dict)
    provider_extras: dict[str, object] = Field(default_factory=dict)
    reasoning_effort: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ModelInvocationResult(BaseSchema):
    """Canonical executor result for one model round-trip."""

    output_items: list[AgentItem] = Field(default_factory=list)
    tool_requests: list[ToolCallRequest] = Field(default_factory=list)
    usage: dict[str, object] = Field(default_factory=dict)
    raw_response: dict[str, object] = Field(default_factory=dict)
    provider_response_id: str | None = None
    provider_request_id: str | None = None
    provider_conversation_id: str | None = None
    continuation: dict[str, object] = Field(default_factory=dict)
    finish_reason: str | None = None


class PendingTurnsResult(BaseSchema):
    """Summary result from one worker pass over queued/active assistant turns."""

    turns_seen: int = 0
    turns_completed: int = 0
    turns_failed: int = 0
    stale_turn_claims_recovered: int = 0
    stale_turns_recovered: int = 0
    stale_tool_invocations_retried: int = 0
    stale_tool_invocations_failed: int = 0
    steps_executed: int = 0
