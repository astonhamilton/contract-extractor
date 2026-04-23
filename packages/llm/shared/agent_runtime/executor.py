from __future__ import annotations

from packages.llm.shared.agent_runtime.models import (
    ModelInvocationRequest,
    ModelInvocationResult,
)


class AgentExecutor:
    """Thin executor contract for one model round-trip."""

    def invoke(self, request: ModelInvocationRequest) -> ModelInvocationResult:
        raise NotImplementedError


class NullAgentExecutor(AgentExecutor):
    """Executor placeholder used when no concrete executor was supplied."""

    def invoke(self, request: ModelInvocationRequest) -> ModelInvocationResult:
        raise NotImplementedError(
            "AgentRuntimeLoop requires an explicit executor. "
            "Pass a concrete AgentExecutor such as LiteLLMAgentExecutor."
        )
