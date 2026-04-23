from __future__ import annotations

from packages.llm.shared.agent_runtime.event_bus import InMemoryRuntimeEventBus
from packages.llm.shared.agent_runtime.events import RuntimeEvent


class PubSubRuntimeEventSink:
    """Publish runtime events into an in-memory bus."""

    def __init__(self, bus: InMemoryRuntimeEventBus) -> None:
        self.bus = bus

    def emit(self, event: RuntimeEvent) -> None:
        """Publish one event into the in-memory event bus."""
        self.bus.emit(event)

