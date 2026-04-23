from __future__ import annotations

from collections.abc import Sequence

from packages.llm.shared.agent_runtime.models import AgentItem
from packages.llm.shared.agent_runtime.providers.base import AgentProvider


class AnthropicAgentProvider(AgentProvider):
    """Anthropic provider-adapter stub for the shared agent runtime."""

    provider_name = "anthropic"

    def build_request(self, items: Sequence[AgentItem], **kwargs: object) -> dict[str, object]:
        return {
            "provider": self.provider_name,
            "items": [item.model_dump(mode="json") for item in items],
            "options": kwargs,
        }

    def execute(self, request: dict[str, object]) -> dict[str, object]:  # pragma: no cover - stub
        raise NotImplementedError("Anthropic agent provider is not implemented yet.")
