from __future__ import annotations

import logging
from dataclasses import dataclass
from threading import Lock
from typing import Callable

from packages.llm.shared.agent_runtime.events import RuntimeEvent, RuntimeEventType

EventHandler = Callable[[RuntimeEvent], None]
LOGGER = logging.getLogger(__name__)


def _normalize_event_types(
    event_types: set[str | RuntimeEventType] | list[str | RuntimeEventType] | tuple[str | RuntimeEventType, ...] | None,
) -> frozenset[RuntimeEventType] | None:
    """Normalize event-type filters into canonical runtime event types."""
    if event_types is None:
        return None
    return frozenset(RuntimeEventType(event_type) for event_type in event_types)


@dataclass(frozen=True)
class RuntimeEventSubscription:
    """One in-memory runtime event subscription."""

    subscription_id: str
    handler: EventHandler
    thread_id: str | None = None
    turn_id: str | None = None
    event_types: frozenset[RuntimeEventType] | None = None


class InMemoryRuntimeEventBus:
    """Thread-safe in-memory pub/sub bus for runtime events."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, RuntimeEventSubscription] = {}
        self._next_id = 0
        self._lock = Lock()

    def subscribe(
        self,
        handler: EventHandler,
        *,
        thread_id: str | None = None,
        turn_id: str | None = None,
        event_types: set[str | RuntimeEventType] | list[str | RuntimeEventType] | tuple[str | RuntimeEventType, ...] | None = None,
    ) -> RuntimeEventSubscription:
        """Register a handler for all events or a filtered subset."""
        with self._lock:
            self._next_id += 1
            subscription = RuntimeEventSubscription(
                subscription_id=f"sub_{self._next_id}",
                handler=handler,
                thread_id=thread_id,
                turn_id=turn_id,
                event_types=_normalize_event_types(event_types),
            )
            self._subscriptions[subscription.subscription_id] = subscription
            return subscription

    def unsubscribe(self, subscription: RuntimeEventSubscription | str) -> None:
        """Remove one subscription from the bus."""
        subscription_id = (
            subscription if isinstance(subscription, str) else subscription.subscription_id
        )
        with self._lock:
            self._subscriptions.pop(subscription_id, None)

    def emit(self, event: RuntimeEvent) -> None:
        """Publish an event to matching subscribers."""
        with self._lock:
            subscriptions = list(self._subscriptions.values())
        for subscription in subscriptions:
            if subscription.thread_id is not None and subscription.thread_id != event.thread_id:
                continue
            if subscription.turn_id is not None and subscription.turn_id != event.turn_id:
                continue
            if (
                subscription.event_types is not None
                and event.event_type not in subscription.event_types
            ):
                continue
            try:
                subscription.handler(event)
            except Exception:  # noqa: BLE001
                LOGGER.exception(
                    "Runtime event subscriber failed event_type=%s subscription_id=%s",
                    event.event_type,
                    subscription.subscription_id,
                )
