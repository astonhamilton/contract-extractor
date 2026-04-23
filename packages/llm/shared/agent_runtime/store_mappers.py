from __future__ import annotations

from packages.data_store.llm_agent_runtime.models import (
    AssistantTurnRecord,
    ItemRecord,
    ModelCallRecord,
    ThreadRecord,
    ToolInvocationRecord,
)
from packages.llm.shared.agent_runtime.models import (
    AgentItem,
    AgentModelCall,
    AgentThread,
    AssistantTurn,
    ToolInvocation,
)


def thread_record_to_runtime(record: ThreadRecord) -> AgentThread:
    """Convert one thread record into the canonical runtime model."""
    return AgentThread(**record.model_dump())


def thread_record_from_runtime(model: AgentThread) -> ThreadRecord:
    """Convert one runtime thread into the DB exchange model."""
    return ThreadRecord(**model.model_dump())


def turn_record_to_runtime(record: AssistantTurnRecord) -> AssistantTurn:
    """Convert one turn record into the canonical runtime model."""
    return AssistantTurn(**record.model_dump())


def turn_record_from_runtime(model: AssistantTurn) -> AssistantTurnRecord:
    """Convert one runtime turn into the DB exchange model."""
    return AssistantTurnRecord(**model.model_dump())


def model_call_record_to_runtime(record: ModelCallRecord) -> AgentModelCall:
    """Convert one model-call record into the canonical runtime model."""
    return AgentModelCall(**record.model_dump())


def model_call_record_from_runtime(model: AgentModelCall) -> ModelCallRecord:
    """Convert one runtime model call into the DB exchange model."""
    return ModelCallRecord(**model.model_dump())


def item_record_to_runtime(record: ItemRecord) -> AgentItem:
    """Convert one item record into the canonical runtime model."""
    return AgentItem(**record.model_dump())


def item_record_from_runtime(model: AgentItem) -> ItemRecord:
    """Convert one runtime item into the DB exchange model."""
    return ItemRecord(**model.model_dump())


def tool_invocation_record_to_runtime(record: ToolInvocationRecord) -> ToolInvocation:
    """Convert one tool-invocation record into the canonical runtime model."""
    return ToolInvocation(**record.model_dump())


def tool_invocation_record_from_runtime(model: ToolInvocation) -> ToolInvocationRecord:
    """Convert one runtime tool invocation into the DB exchange model."""
    return ToolInvocationRecord(**model.model_dump())
