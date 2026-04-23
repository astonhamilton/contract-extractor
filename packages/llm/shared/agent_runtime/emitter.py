from __future__ import annotations

import logging
from typing import Protocol

from packages.llm.shared.agent_runtime.events import RuntimeEvent

LOGGER = logging.getLogger(__name__)


class RuntimeEventEmitter(Protocol):
    """Protocol for runtime telemetry emitters."""

    def emit(self, event: RuntimeEvent) -> None:
        """Publish one runtime event."""


class NullRuntimeEventEmitter:
    """No-op runtime event emitter."""

    def emit(self, event: RuntimeEvent) -> None:
        """Ignore a runtime event."""
        del event


class CompositeRuntimeEventEmitter:
    """Fan out runtime events to multiple emitters."""

    def __init__(self, emitters: list[RuntimeEventEmitter] | None = None) -> None:
        self.emitters = emitters or []

    def emit(self, event: RuntimeEvent) -> None:
        """Forward a runtime event to every child emitter."""
        for emitter in self.emitters:
            try:
                emitter.emit(event)
            except Exception:  # noqa: BLE001
                LOGGER.exception(
                    "Runtime event emitter failed event_type=%s emitter=%s",
                    event.event_type,
                    type(emitter).__name__,
                )
