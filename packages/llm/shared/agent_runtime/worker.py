from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime

from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.emitter import NullRuntimeEventEmitter, RuntimeEventEmitter
from packages.llm.shared.agent_runtime.events import RuntimeEvent, RuntimeEventType, WorkerRunOncePayload
from packages.llm.shared.agent_runtime.loop import AgentRuntimeLoop
from packages.llm.shared.agent_runtime.models import PendingTurnsResult, new_id
from packages.schemas.common import BaseSchema

PassCallback = Callable[["WorkerPassResult"], None]


def _utc_now() -> datetime:
    """Return the current UTC wall-clock time."""
    return datetime.now(UTC)


class WorkerPassResult(BaseSchema):
    """Summary from one stateless worker pass."""

    started_at: datetime
    finished_at: datetime
    pending_turns: PendingTurnsResult

    @property
    def duration_seconds(self) -> float:
        """Return the wall-clock duration of the pass in seconds."""
        return max((self.finished_at - self.started_at).total_seconds(), 0.0)

    @property
    def did_work(self) -> bool:
        """Return whether the pass observed or performed any meaningful work."""
        result = self.pending_turns
        return any(
            (
                result.turns_seen,
                result.turns_completed,
                result.turns_failed,
                result.steps_executed,
                result.stale_turns_recovered,
                result.stale_tool_invocations_retried,
                result.stale_tool_invocations_failed,
            )
        )


class AgentRuntimeWorker:
    """Stateless background worker wrapper around the queued agent runtime loop."""

    def __init__(
        self,
        *,
        db: SqliteDb,
        loop: AgentRuntimeLoop,
        emitter: RuntimeEventEmitter | None = None,
    ) -> None:
        self.db = db
        self.loop = loop
        self.emitter = emitter or NullRuntimeEventEmitter()
        self.worker_id = new_id("worker")

    def run_once(
        self,
        *,
        max_turns: int = 10,
        max_steps: int = 100,
        thread_id: str | None = None,
    ) -> WorkerPassResult:
        """Run a single stateless worker pass over pending assistant turns."""
        started_at = _utc_now()
        pending_turns = self.loop.run_pending_turns(
            self.db,
            worker_id=self.worker_id,
            max_turns=max_turns,
            max_steps=max_steps,
            thread_id=thread_id,
        )
        finished_at = _utc_now()
        result = WorkerPassResult(
            started_at=started_at,
            finished_at=finished_at,
            pending_turns=pending_turns,
        )
        if result.did_work:
            self.emitter.emit(
                RuntimeEvent(
                    event_id=f"evt_worker_pass_{finished_at.timestamp()}",
                    event_type=RuntimeEventType.WORKER_RUN_ONCE_COMPLETED,
                    worker_id=self.worker_id,
                    payload=WorkerRunOncePayload.model_validate(result.model_dump(mode="json")).model_dump(
                        mode="json"
                    ),
                )
            )
        return result

    def run_forever(
        self,
        *,
        max_turns: int = 10,
        max_steps: int = 100,
        thread_id: str | None = None,
        poll_interval_seconds: float = 0.5,
        on_pass: PassCallback | None = None,
    ) -> None:
        """Continuously process pending assistant turns until interrupted."""
        while True:
            result = self.run_once(
                max_turns=max_turns,
                max_steps=max_steps,
                thread_id=thread_id,
            )
            if on_pass is not None:
                on_pass(result)
            if not result.did_work:
                time.sleep(poll_interval_seconds)
