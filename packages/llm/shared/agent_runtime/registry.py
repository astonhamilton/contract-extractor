from __future__ import annotations

from collections.abc import Callable, Iterable

from packages.llm.shared.agent_runtime.models import AgentSpec

AgentSpecBuilder = Callable[[], AgentSpec]


def _static_builder(spec: AgentSpec) -> AgentSpecBuilder:
    """Return a builder that yields deep copies of one static agent spec."""

    def _build() -> AgentSpec:
        return spec.model_copy(deep=True)

    return _build


class AgentRegistry:
    """Immutable registry of agent-spec builders addressable by persisted agent id."""

    def __init__(self, agent_specs_or_builders: Iterable[AgentSpec | AgentSpecBuilder]) -> None:
        builders: dict[str, AgentSpecBuilder] = {}
        for entry in agent_specs_or_builders:
            builder = _static_builder(entry) if isinstance(entry, AgentSpec) else entry
            spec = builder()
            if spec.agent_id in builders:
                raise ValueError(f"Duplicate agent_id={spec.agent_id!r} in AgentRegistry.")
            builders[spec.agent_id] = builder
        if not builders:
            raise ValueError("AgentRegistry requires at least one AgentSpec or builder.")
        self._builders = builders

    def get(self, agent_id: str) -> AgentSpec | None:
        """Return one freshly built agent spec by id when present."""
        builder = self._builders.get(agent_id)
        return None if builder is None else builder()

    def require(self, agent_id: str) -> AgentSpec:
        """Return one freshly built agent spec by id or raise a useful error."""
        spec = self.get(agent_id)
        if spec is None:
            known = ", ".join(sorted(self._builders))
            raise ValueError(f"Unknown agent_id={agent_id!r}. Known agents: {known}")
        return spec

    def all(self) -> list[AgentSpec]:
        """Return all registered agent specs ordered by agent id."""
        return [self._builders[agent_id]() for agent_id in sorted(self._builders)]

