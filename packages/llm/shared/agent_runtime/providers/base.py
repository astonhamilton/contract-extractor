from __future__ import annotations

from collections.abc import Sequence

from packages.llm.shared.agent_runtime.models import AgentItem


class AgentProvider:
    """Provider adapter interface for the shared agent runtime."""

    provider_name: str = "unknown"

    def build_request(self, items: Sequence[AgentItem], **kwargs: object) -> dict[str, object]:
        """Build a provider-native request payload from canonical thread items."""
        raise NotImplementedError

    def execute(self, request: dict[str, object]) -> dict[str, object]:
        """Execute a provider-native request and return the raw response payload."""
        raise NotImplementedError
