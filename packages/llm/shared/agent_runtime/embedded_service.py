from __future__ import annotations

import logging
import threading

from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.executor import AgentExecutor
from packages.llm.shared.agent_runtime.emitter import RuntimeEventEmitter
from packages.llm.shared.agent_runtime.event_bus import InMemoryRuntimeEventBus
from packages.llm.shared.agent_runtime.loop import AgentRuntimeLoop
from packages.llm.shared.agent_runtime.registry import AgentRegistry
from packages.llm.shared.agent_runtime.tools import ToolRegistry
from packages.llm.shared.agent_runtime.tools import ToolExecutionContext
from packages.llm.shared.agent_runtime.worker import AgentRuntimeWorker


LOGGER = logging.getLogger(__name__)


class EmbeddedAgentRuntimeService:
    """Reusable in-process host for a background agent-runtime worker."""

    def __init__(
        self,
        *,
        worker: AgentRuntimeWorker,
        event_bus: InMemoryRuntimeEventBus,
        event_emitter: RuntimeEventEmitter,
        enabled: bool = True,
        poll_interval_seconds: float = 0.5,
        max_turns: int = 25,
        max_steps: int = 200,
        thread_name: str = "embedded-agent-runtime-worker",
    ) -> None:
        self.event_bus = event_bus
        self.event_emitter = event_emitter
        self.enabled = enabled
        self.poll_interval_seconds = poll_interval_seconds
        self.max_turns = max_turns
        self.max_steps = max_steps
        self.thread_name = thread_name
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._worker = worker

    @property
    def loop(self) -> AgentRuntimeLoop:
        """Return the shared immutable runtime loop used by the worker."""
        return self._worker.loop

    def start(self) -> None:
        """Start the embedded background worker thread when enabled."""
        if not self.enabled:
            LOGGER.info("Embedded agent runtime worker disabled")
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_forever,
            daemon=True,
            name=self.thread_name,
        )
        self._thread.start()
        LOGGER.info(
            "Embedded agent runtime worker started max_turns=%s max_steps=%s poll_interval=%.2fs",
            self.max_turns,
            self.max_steps,
            self.poll_interval_seconds,
        )

    def stop(self) -> None:
        """Stop the embedded background worker thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(self.poll_interval_seconds * 4, 2.0))
        self._thread = None
        LOGGER.info("Embedded agent runtime worker stopped")

    def _run_forever(self) -> None:
        """Continuously run worker passes until stop is requested."""
        while not self._stop_event.is_set():
            try:
                result = self._worker.run_once(
                    max_turns=self.max_turns,
                    max_steps=self.max_steps,
                )
            except Exception:  # noqa: BLE001
                LOGGER.exception("Embedded agent runtime worker pass failed")
                self._stop_event.wait(self.poll_interval_seconds)
                continue
            if not result.did_work:
                self._stop_event.wait(self.poll_interval_seconds)


def build_embedded_agent_runtime_service(
    *,
    db: SqliteDb,
    agent_registry: AgentRegistry,
    tools: ToolRegistry | None = None,
    tool_context: ToolExecutionContext | None = None,
    executor: AgentExecutor | None = None,
    event_bus: InMemoryRuntimeEventBus,
    event_emitter: RuntimeEventEmitter,
    enabled: bool = True,
    poll_interval_seconds: float = 0.5,
    max_turns: int = 25,
    max_steps: int = 200,
    thread_name: str = "embedded-agent-runtime-worker",
) -> EmbeddedAgentRuntimeService:
    """Build an embeddable agent-runtime service from runtime components."""
    loop = AgentRuntimeLoop(
        agent_registry=agent_registry,
        tools=tools,
        tool_context=tool_context,
        executor=executor,
        emitter=event_emitter,
    )
    worker = AgentRuntimeWorker(
        db=db,
        loop=loop,
        emitter=event_emitter,
    )
    return EmbeddedAgentRuntimeService(
        worker=worker,
        event_bus=event_bus,
        event_emitter=event_emitter,
        enabled=enabled,
        poll_interval_seconds=poll_interval_seconds,
        max_turns=max_turns,
        max_steps=max_steps,
        thread_name=thread_name,
    )
