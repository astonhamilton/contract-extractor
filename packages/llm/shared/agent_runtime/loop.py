from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime, timedelta

from packages.data_store.connect import SqliteDb, sqlite_transaction
from packages.data_store.llm_agent_runtime import commands, queries
from packages.llm.shared.agent_runtime.emitter import NullRuntimeEventEmitter, RuntimeEventEmitter
from packages.llm.shared.agent_runtime.events import (
    ErrorPayload,
    ModelCallCompletedPayload,
    ModelCallCreatedPayload,
    ModelCallStartedPayload,
    RuntimeEvent,
    RuntimeEventType,
    ThreadCreatedPayload,
    ToolInvocationCompletedPayload,
    ToolInvocationStalePayload,
    ToolInvocationStartedPayload,
    TurnClaimedPayload,
    TurnEnqueuedPayload,
    TurnFailedPayload,
    TurnPhaseChangedPayload,
    TurnTerminalPayload,
    WorkerPassPayload,
    payload_dict,
)
from packages.llm.shared.agent_runtime.executor import AgentExecutor, NullAgentExecutor
from packages.llm.shared.agent_runtime.heartbeat import background_heartbeat
from packages.llm.shared.agent_runtime.models import (
    AgentItem,
    AgentModelCall,
    AgentSpec,
    AgentThread,
    AssistantTurn,
    ExecutionOptions,
    ModelInvocationRequest,
    PendingTurnsResult,
    ToolCallRequest,
    ToolInvocation,
    new_id,
)
from packages.llm.shared.agent_runtime.registry import AgentRegistry
from packages.llm.shared.agent_runtime import store_mappers
from packages.llm.shared.agent_runtime.tools import ToolRegistry
from packages.llm.shared.agent_runtime.tools import ToolExecutionContext

LOGGER = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _merge_usage(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
    merged = dict(left)
    for key, value in right.items():
        if isinstance(value, int) and isinstance(merged.get(key), int):
            merged[key] = int(merged[key]) + value
        elif key not in merged:
            merged[key] = value
        else:
            merged[key] = value
    return merged


def _stale_before(timeout_seconds: int) -> datetime:
    """Return the heartbeat cutoff for abandoned work."""
    return _now() - timedelta(seconds=timeout_seconds)


def _thread_has_provider_native_history(items: list[AgentItem]) -> bool:
    """Return True when thread history includes provider-native replay-sensitive items."""
    return any(item.item_type in {"reasoning", "hosted_tool_event"} for item in items)


class AgentRuntimeLoop:
    """Durable queued runtime loop for assistant turns with tool execution."""

    def __init__(
        self,
        *,
        agent_registry: AgentRegistry,
        tools: ToolRegistry | None = None,
        tool_context: ToolExecutionContext | None = None,
        executor: AgentExecutor | None = None,
        emitter: RuntimeEventEmitter | None = None,
        turn_heartbeat_interval_seconds: float = 1.0,
        turn_heartbeat_timeout_seconds: int = 30,
        model_call_heartbeat_interval_seconds: float = 1.0,
        model_call_heartbeat_timeout_seconds: int = 120,
        tool_invocation_heartbeat_interval_seconds: float = 1.0,
        tool_invocation_heartbeat_timeout_seconds: int = 120,
    ) -> None:
        self.agent_registry = agent_registry
        self.tools = tools or ToolRegistry()
        self.tool_context = tool_context or ToolExecutionContext()
        if self.tool_context.runtime_loop is None:
            self.tool_context.runtime_loop = self
        self.executor = executor or NullAgentExecutor()
        self.emitter = emitter or NullRuntimeEventEmitter()
        self.turn_heartbeat_interval_seconds = turn_heartbeat_interval_seconds
        self.turn_heartbeat_timeout_seconds = turn_heartbeat_timeout_seconds
        self.model_call_heartbeat_interval_seconds = model_call_heartbeat_interval_seconds
        self.model_call_heartbeat_timeout_seconds = model_call_heartbeat_timeout_seconds
        self.tool_invocation_heartbeat_interval_seconds = tool_invocation_heartbeat_interval_seconds
        self.tool_invocation_heartbeat_timeout_seconds = tool_invocation_heartbeat_timeout_seconds
        self._validate_tool_coverage()

    def _validate_tool_coverage(self) -> None:
        """Fail fast when registered agents reference unknown local tools."""
        missing: list[str] = []
        for spec in self.agent_registry.all():
            for tool in spec.local_tools:
                if self.tools.get_definition(tool.name) is None:
                    missing.append(f"{spec.agent_id}:{tool.name}")
        if missing:
            raise ValueError(
                "AgentRuntimeLoop is missing tool handlers for: " + ", ".join(sorted(missing))
            )

    def _agent_spec_for_id(self, agent_id: str) -> AgentSpec:
        """Return the registered agent spec for one persisted id."""
        return self.agent_registry.require(agent_id)

    def _resolve_thread_execution_options(
        self,
        agent_spec: AgentSpec,
        override: ExecutionOptions | None = None,
    ) -> ExecutionOptions:
        """Resolve one thread's default execution options from agent defaults plus overrides."""
        override = override or ExecutionOptions()
        return ExecutionOptions(
            provider=override.provider or agent_spec.default_provider,
            model=override.model or agent_spec.default_model,
            continuity_mode=override.continuity_mode or "stateless",
            provider_extras=dict(override.provider_extras),
            reasoning_effort=override.reasoning_effort,
        )

    def _resolve_turn_execution_options(
        self,
        *,
        thread: AgentThread,
        override: ExecutionOptions | None = None,
    ) -> ExecutionOptions:
        """Resolve one turn's execution options from thread defaults plus per-turn overrides."""
        override = override or ExecutionOptions()
        base = thread.execution_options
        return ExecutionOptions(
            provider=override.provider or base.provider,
            model=override.model or base.model,
            continuity_mode=override.continuity_mode or base.continuity_mode or "stateless",
            provider_extras={**base.provider_extras, **override.provider_extras},
            reasoning_effort=(
                override.reasoning_effort
                if override.reasoning_effort is not None
                else base.reasoning_effort
            ),
        )

    def _emit(
        self,
        event_type: RuntimeEventType,
        *,
        worker_id: str | None = None,
        thread_id: str | None = None,
        turn_id: str | None = None,
        model_call_id: str | None = None,
        tool_invocation_id: str | None = None,
        payload: dict[str, object] | object | None = None,
    ) -> None:
        """Emit one structured runtime event."""
        self.emitter.emit(
            RuntimeEvent(
                event_id=new_id("evt"),
                event_type=event_type,
                thread_id=thread_id,
                turn_id=turn_id,
                model_call_id=model_call_id,
                tool_invocation_id=tool_invocation_id,
                worker_id=worker_id,
                payload=payload_dict(payload),
            )
        )

    def _make_event(
        self,
        event_type: RuntimeEventType,
        *,
        worker_id: str | None = None,
        thread_id: str | None = None,
        turn_id: str | None = None,
        model_call_id: str | None = None,
        tool_invocation_id: str | None = None,
        payload: dict[str, object] | object | None = None,
    ) -> RuntimeEvent:
        """Build one runtime event without publishing it yet."""
        return RuntimeEvent(
            event_id=new_id("evt"),
            event_type=event_type,
            thread_id=thread_id,
            turn_id=turn_id,
            model_call_id=model_call_id,
            tool_invocation_id=tool_invocation_id,
            worker_id=worker_id,
            payload=payload_dict(payload),
        )

    def _emit_buffered(self, events: list[RuntimeEvent]) -> None:
        """Publish buffered events after the associated DB transaction commits."""
        for event in events:
            self.emitter.emit(event)

    def start_thread(
        self,
        db: SqliteDb,
        *,
        agent_id: str,
        title: str | None = None,
        metadata: dict[str, object] | None = None,
        initial_user_text: str | None = None,
        execution_options: ExecutionOptions | None = None,
    ) -> tuple[AgentThread, AssistantTurn | None]:
        """Create a thread and optionally enqueue the first turn with user input."""
        with db.connect() as connection:
            result = self._start_thread_with_connection(
                connection,
                agent_id=agent_id,
                title=title,
                metadata=metadata,
                initial_user_text=initial_user_text,
                execution_options=execution_options,
            )
            connection.commit()
            return result

    def _start_thread_with_connection(
        self,
        connection: sqlite3.Connection,
        *,
        agent_id: str,
        title: str | None = None,
        metadata: dict[str, object] | None = None,
        initial_user_text: str | None = None,
        execution_options: ExecutionOptions | None = None,
    ) -> tuple[AgentThread, AssistantTurn | None]:
        """Create a thread and optionally enqueue the first turn with user input."""
        agent_spec = self.agent_registry.require(agent_id)
        buffered_events: list[RuntimeEvent] = []
        with sqlite_transaction(connection):
            thread = AgentThread(
                thread_kind="conversation",
                agent_id=agent_spec.agent_id,
                title=title,
                execution_options=self._resolve_thread_execution_options(
                    agent_spec,
                    execution_options,
                ),
                metadata=metadata or {},
            )
            created_record = commands.create_thread(
                connection,
                store_mappers.thread_record_from_runtime(thread),
            )
            persisted_thread = store_mappers.thread_record_to_runtime(created_record)
            if not initial_user_text:
                buffered_events.append(
                    self._make_event(
                        RuntimeEventType.THREAD_CREATED,
                        thread_id=persisted_thread.thread_id,
                        payload=ThreadCreatedPayload(
                            thread_kind=persisted_thread.thread_kind,
                            agent_id=persisted_thread.agent_id,
                            title=persisted_thread.title,
                        ),
                    )
                )
                result = (persisted_thread, None)
            else:
                turn = self._send_input_with_connection(
                    connection,
                    persisted_thread.thread_id,
                    initial_user_text,
                    execution_options=execution_options,
                    buffered_events=buffered_events,
                )
                latest_thread = queries.get_thread(connection, persisted_thread.thread_id) or created_record
                buffered_events.append(
                    self._make_event(
                        RuntimeEventType.THREAD_CREATED,
                        thread_id=persisted_thread.thread_id,
                        turn_id=turn.turn_id if turn is not None else None,
                        payload=ThreadCreatedPayload(
                            thread_kind=persisted_thread.thread_kind,
                            agent_id=persisted_thread.agent_id,
                            title=persisted_thread.title,
                            initial_input=True,
                        ),
                    )
                )
                result = (store_mappers.thread_record_to_runtime(latest_thread), turn)
        self._emit_buffered(buffered_events)
        return result

    def start_task(
        self,
        db: SqliteDb,
        *,
        agent_id: str,
        task_text: str,
        title: str | None = None,
        metadata: dict[str, object] | None = None,
        execution_options: ExecutionOptions | None = None,
    ) -> tuple[AgentThread, AssistantTurn]:
        """Create a single-shot task thread and enqueue its only intended turn."""
        with db.connect() as connection:
            result = self._start_task_with_connection(
                connection,
                agent_id=agent_id,
                task_text=task_text,
                title=title,
                metadata=metadata,
                execution_options=execution_options,
            )
            connection.commit()
            return result

    def _start_task_with_connection(
        self,
        connection: sqlite3.Connection,
        *,
        agent_id: str,
        task_text: str,
        title: str | None = None,
        metadata: dict[str, object] | None = None,
        execution_options: ExecutionOptions | None = None,
    ) -> tuple[AgentThread, AssistantTurn]:
        """Create a single-shot task thread and enqueue its only intended turn."""
        agent_spec = self.agent_registry.require(agent_id)
        buffered_events: list[RuntimeEvent] = []
        with sqlite_transaction(connection):
            thread = AgentThread(
                thread_kind="task",
                agent_id=agent_spec.agent_id,
                title=title,
                execution_options=self._resolve_thread_execution_options(
                    agent_spec,
                    execution_options,
                ),
                metadata=metadata or {},
            )
            created_record = commands.create_thread(
                connection,
                store_mappers.thread_record_from_runtime(thread),
            )
            persisted_thread = store_mappers.thread_record_to_runtime(created_record)
            turn = self._send_input_with_connection(
                connection,
                persisted_thread.thread_id,
                task_text,
                execution_options=execution_options,
                buffered_events=buffered_events,
            )
            latest_thread = queries.get_thread(connection, persisted_thread.thread_id) or created_record
            buffered_events.append(
                self._make_event(
                    RuntimeEventType.THREAD_CREATED,
                    thread_id=persisted_thread.thread_id,
                    turn_id=turn.turn_id,
                    payload=ThreadCreatedPayload(
                        thread_kind=persisted_thread.thread_kind,
                        agent_id=persisted_thread.agent_id,
                        title=persisted_thread.title,
                        initial_input=True,
                    ),
                )
            )
            result = (store_mappers.thread_record_to_runtime(latest_thread), turn)
        self._emit_buffered(buffered_events)
        return result

    def send_input(
        self,
        db: SqliteDb,
        thread_id: str,
        user_text: str,
        *,
        execution_options: ExecutionOptions | None = None,
        metadata: dict[str, object] | None = None,
    ) -> AssistantTurn:
        """Append one user input item and enqueue a queued turn for the thread."""
        with db.connect() as connection:
            result = self._send_input_with_connection(
                connection,
                thread_id,
                user_text,
                execution_options=execution_options,
                metadata=metadata,
            )
            connection.commit()
            return result

    def _send_input_with_connection(
        self,
        connection: sqlite3.Connection,
        thread_id: str,
        user_text: str,
        *,
        execution_options: ExecutionOptions | None = None,
        metadata: dict[str, object] | None = None,
        buffered_events: list[RuntimeEvent] | None = None,
    ) -> AssistantTurn:
        """Append one user input item and enqueue a queued turn for the thread."""
        owns_event_buffer = buffered_events is None
        events = [] if buffered_events is None else buffered_events
        with sqlite_transaction(connection):
            thread_record = queries.get_thread(connection, thread_id)
            if thread_record is None:
                raise ValueError(f"Unknown thread: {thread_id}")
            thread = store_mappers.thread_record_to_runtime(thread_record)
            if thread.active_turn_id:
                raise ValueError(f"Thread already has active turn: {thread.active_turn_id}")

            turn = AssistantTurn(
                thread_id=thread_id,
                agent_id=thread.agent_id,
                execution_options=self._resolve_turn_execution_options(
                    thread=thread,
                    override=execution_options,
                ),
                metadata=metadata or {},
            )
            persisted_turn = store_mappers.turn_record_to_runtime(
                commands.create_turn(
                    connection,
                    store_mappers.turn_record_from_runtime(turn),
                )
            )
            commands.append_items(
                connection,
                [
                    store_mappers.item_record_from_runtime(
                        AgentItem(
                            thread_id=thread_id,
                            turn_id=persisted_turn.turn_id,
                            item_type="message",
                            role="user",
                            content_text=user_text,
                        )
                    )
                ],
            )
            updated_thread = commands.activate_thread_for_new_turn(
                connection,
                thread_id=thread.thread_id,
                turn_id=persisted_turn.turn_id,
                status="running",
                phase="created",
            )
            if updated_thread is None:
                raise ValueError(f"Thread already has active turn: {thread.thread_id}")
            LOGGER.info(
                "Enqueued assistant turn %s on thread %s provider=%s model=%s",
                persisted_turn.turn_id,
                thread_id,
                persisted_turn.execution_options.provider,
                persisted_turn.execution_options.model,
            )
            events.append(
                self._make_event(
                    RuntimeEventType.TURN_ENQUEUED,
                    thread_id=thread_id,
                    turn_id=persisted_turn.turn_id,
                    payload=TurnEnqueuedPayload(
                        agent_id=persisted_turn.agent_id,
                        provider=persisted_turn.execution_options.provider,
                        model=persisted_turn.execution_options.model,
                    ),
                )
            )
            result = persisted_turn
        if owns_event_buffer:
            self._emit_buffered(events)
        return result

    def run_pending_turns(
        self,
        db: SqliteDb,
        *,
        worker_id: str | None = None,
        max_turns: int = 10,
        max_steps: int = 100,
        thread_id: str | None = None,
    ) -> PendingTurnsResult:
        """Run queued/active assistant turns until the worker budget is exhausted."""
        with db.connect() as connection:
            result = self._run_pending_turns_with_connection(
                connection,
                db=db,
                worker_id=worker_id,
                max_turns=max_turns,
                max_steps=max_steps,
                thread_id=thread_id,
            )
            connection.commit()
            return result

    def _run_pending_turns_with_connection(
        self,
        connection: sqlite3.Connection,
        *,
        db: SqliteDb,
        worker_id: str | None = None,
        max_turns: int = 10,
        max_steps: int = 100,
        thread_id: str | None = None,
    ) -> PendingTurnsResult:
        """Run queued/active assistant turns until the worker budget is exhausted."""
        worker_id = worker_id or new_id("worker")
        result = PendingTurnsResult()
        stale_turn_claim_ids = commands.recover_stale_turn_claims(
            connection,
            stale_before=_stale_before(self.turn_heartbeat_timeout_seconds),
        )
        result.stale_turn_claims_recovered = len(stale_turn_claim_ids)
        for turn_id in stale_turn_claim_ids:
            self._emit(
                RuntimeEventType.TURN_STALE_CLAIM_RECOVERED,
                worker_id=worker_id,
                turn_id=turn_id,
            )
        stale_turn_ids = commands.recover_stale_model_calls(
            connection,
            stale_before=_stale_before(self.model_call_heartbeat_timeout_seconds),
            error_message="Model call heartbeat expired before completion.",
        )
        result.stale_turns_recovered = len(stale_turn_ids)
        tool_retry_count, tool_fail_count = self._recover_stale_tool_invocations(
            connection,
            worker_id=worker_id,
        )
        result.stale_tool_invocations_retried = tool_retry_count
        result.stale_tool_invocations_failed = tool_fail_count
        steps_remaining = max_steps
        LOGGER.info(
            "run_pending_turns starting turns_seen=%s stale_turn_claims_recovered=%s stale_turns_recovered=%s stale_tool_invocations_retried=%s stale_tool_invocations_failed=%s max_turns=%s max_steps=%s thread_id=%s",
            result.turns_seen,
            result.stale_turn_claims_recovered,
            result.stale_turns_recovered,
            result.stale_tool_invocations_retried,
            result.stale_tool_invocations_failed,
            max_turns,
            max_steps,
            thread_id,
        )
        for _ in range(max_turns):
            turn = self._claim_next_turn(connection, thread_id=thread_id, worker_id=worker_id)
            if turn is None:
                break
            result.turns_seen += 1
            LOGGER.info(
                "Picked up turn %s thread=%s status=%s phase=%s",
                turn.turn_id,
                turn.thread_id,
                turn.status,
                turn.phase,
            )
            with background_heartbeat(
                interval_seconds=self.turn_heartbeat_interval_seconds,
                callback=self._build_turn_heartbeat_updater(
                    db,
                    turn.turn_id,
                    worker_id=worker_id,
                ),
            ):
                while steps_remaining > 0 and (
                    turn.status in {"queued", "active"} or turn.phase in {"completed", "failed"}
                ):
                    LOGGER.info(
                        "Executing turn step turn=%s thread=%s status=%s phase=%s steps_remaining=%s",
                        turn.turn_id,
                        turn.thread_id,
                        turn.status,
                        turn.phase,
                        steps_remaining,
                    )
                    turn = self._step_turn(
                        connection,
                        turn,
                        worker_id=worker_id,
                        db=db,
                    )
                    result.steps_executed += 1
                    steps_remaining -= 1
                    if turn.status in {"completed", "failed"} and turn.phase in {"completed", "failed"}:
                        break
            if turn.status == "completed":
                result.turns_completed += 1
            elif turn.status == "failed":
                result.turns_failed += 1
            LOGGER.info(
                "Turn finished pass turn=%s final_status=%s final_phase=%s",
                turn.turn_id,
                turn.status,
                turn.phase,
            )
        LOGGER.info(
            "run_pending_turns finished turns_completed=%s turns_failed=%s stale_turn_claims_recovered=%s stale_turns_recovered=%s stale_tool_invocations_retried=%s stale_tool_invocations_failed=%s steps_executed=%s",
            result.turns_completed,
            result.turns_failed,
            result.stale_turn_claims_recovered,
            result.stale_turns_recovered,
            result.stale_tool_invocations_retried,
            result.stale_tool_invocations_failed,
            result.steps_executed,
        )
        if any(
            (
                result.turns_seen,
                result.turns_completed,
                result.turns_failed,
                result.stale_turn_claims_recovered,
                result.stale_turns_recovered,
                result.stale_tool_invocations_retried,
                result.stale_tool_invocations_failed,
                result.steps_executed,
            )
        ):
            self._emit(
                RuntimeEventType.WORKER_PASS_COMPLETED,
                worker_id=worker_id,
                payload=WorkerPassPayload.model_validate(result.model_dump(mode="json")),
            )
        return result

    def _claim_next_turn(
        self,
        connection: sqlite3.Connection,
        *,
        thread_id: str | None,
        worker_id: str,
    ) -> AssistantTurn | None:
        """Atomically select and claim the next runnable turn for this worker."""
        claimed_record = commands.claim_next_runnable_turn(
            connection,
            worker_id=worker_id,
            heartbeat_at=_now(),
            stale_before=_now() - timedelta(seconds=self.turn_heartbeat_timeout_seconds),
            thread_id=thread_id,
        )
        if claimed_record is None:
            return None
        claimed_turn = store_mappers.turn_record_to_runtime(claimed_record)
        self._emit(
            RuntimeEventType.TURN_CLAIMED,
            worker_id=worker_id,
            thread_id=claimed_turn.thread_id,
            turn_id=claimed_turn.turn_id,
            payload=TurnClaimedPayload(
                worker_id=worker_id,
                phase=claimed_turn.phase,
                status=claimed_turn.status,
            ),
        )
        return claimed_turn

    def _recover_stale_tool_invocations(
        self,
        connection: sqlite3.Connection,
        *,
        worker_id: str,
    ) -> tuple[int, int]:
        """Recover stale leased tool invocations based on tool retry policy."""
        retried = 0
        failed = 0
        stale_before = _stale_before(self.tool_invocation_heartbeat_timeout_seconds)
        stale_invocations = queries.list_stale_tool_invocations(
            connection,
            stale_before=stale_before,
        )
        for invocation_record in stale_invocations:
            invocation = store_mappers.tool_invocation_record_to_runtime(invocation_record)
            definition = self.tools.get_definition(invocation.tool_name)
            error_text = "Tool invocation lease expired before completion."
            if definition is None or definition.retry_on_stale:
                try:
                    commands.reset_stale_tool_invocation(
                        connection,
                        invocation=invocation_record,
                        stale_before=stale_before,
                    )
                except RuntimeError:
                    continue
                self._emit(
                    RuntimeEventType.TOOL_INVOCATION_STALE_RETRIED,
                    worker_id=worker_id,
                    thread_id=invocation.thread_id,
                    turn_id=invocation.turn_id,
                    tool_invocation_id=invocation.tool_invocation_id,
                    payload=ToolInvocationStalePayload(tool_name=invocation.tool_name),
                )
                retried += 1
                continue

            thread_record = queries.get_thread(connection, invocation.thread_id)
            turn_record = queries.get_turn(connection, invocation.turn_id or "")
            if thread_record is not None and turn_record is not None:
                try:
                    commands.fail_stale_tool_invocation_turn(
                        connection,
                        invocation=invocation_record,
                        thread=thread_record,
                        turn=turn_record,
                        error_text=error_text,
                        stale_before=stale_before,
                    )
                except RuntimeError:
                    continue
            else:
                try:
                    commands.fail_stale_tool_invocation(
                        connection,
                        invocation=invocation_record,
                        error_text=error_text,
                        stale_before=stale_before,
                    )
                except RuntimeError:
                    continue
            self._emit(
                RuntimeEventType.TOOL_INVOCATION_STALE_FAILED,
                worker_id=worker_id,
                thread_id=invocation.thread_id,
                turn_id=invocation.turn_id,
                tool_invocation_id=invocation.tool_invocation_id,
                payload=ToolInvocationStalePayload(tool_name=invocation.tool_name, error=error_text),
            )
            failed += 1
        return retried, failed

    def _step_turn(
        self,
        connection: sqlite3.Connection,
        turn: AssistantTurn,
        *,
        worker_id: str,
        db: SqliteDb,
    ) -> AssistantTurn:
        thread_record = queries.get_thread(connection, turn.thread_id)
        if thread_record is None:
            raise ValueError(f"Missing thread for turn: {turn.turn_id}")
        thread = store_mappers.thread_record_to_runtime(thread_record)
        agent_spec = self._agent_spec_for_id(turn.agent_id)
        if turn.phase == "created":
            return self._handle_created(connection, thread, turn, worker_id=worker_id)
        if turn.phase == "assembling_context":
            return self._handle_assembling_context(
                connection,
                agent_spec,
                thread,
                turn,
                worker_id=worker_id,
            )
        if turn.phase == "executing_model":
            return self._handle_executing_model(
                connection,
                thread,
                turn,
                worker_id=worker_id,
                db=db,
            )
        if turn.phase == "executing_tools":
            return self._handle_executing_tools(
                connection,
                thread,
                turn,
                worker_id=worker_id,
                db=db,
            )
        if turn.phase == "completed":
            return self._handle_completed(connection, thread, turn, worker_id=worker_id)
        if turn.phase == "failed":
            return self._handle_failed(connection, thread, turn, worker_id=worker_id)
        raise ValueError(f"Unsupported turn phase: {turn.phase}")

    def _handle_created(
        self,
        connection: sqlite3.Connection,
        thread: AgentThread,
        turn: AssistantTurn,
        *,
        worker_id: str,
    ) -> AssistantTurn:
        LOGGER.info("Assistant turn %s transitioning created -> assembling_context", turn.turn_id)
        updated_thread = thread.model_copy(
            update={
                "status": "running",
                "phase": "assembling_context",
                "active_turn_id": turn.turn_id,
            }
        )
        updated_turn = turn.model_copy(update={"status": "active", "phase": "assembling_context"})
        _thread_record, turn_record = commands.begin_turn_context(
            connection,
            thread=store_mappers.thread_record_from_runtime(updated_thread),
            turn=store_mappers.turn_record_from_runtime(updated_turn),
        )
        persisted_turn = store_mappers.turn_record_to_runtime(turn_record)
        self._emit(
            RuntimeEventType.TURN_PHASE_CHANGED,
            worker_id=worker_id,
            thread_id=thread.thread_id,
            turn_id=persisted_turn.turn_id,
            payload=TurnPhaseChangedPayload(phase=persisted_turn.phase, status=persisted_turn.status),
        )
        return persisted_turn

    def _handle_assembling_context(
        self,
        connection: sqlite3.Connection,
        agent_spec: AgentSpec,
        thread: AgentThread,
        turn: AssistantTurn,
        *,
        worker_id: str,
    ) -> AssistantTurn:
        items = [
            store_mappers.item_record_to_runtime(record)
            for record in queries.list_items(connection, thread.thread_id)
        ]
        latest_model_call_record = queries.get_latest_model_call(connection, turn.turn_id)
        latest_model_call = (
            None
            if latest_model_call_record is None
            else store_mappers.model_call_record_to_runtime(latest_model_call_record)
        )
        requested_provider = turn.execution_options.provider or agent_spec.default_provider
        historical_providers = {
            persisted_turn.execution_options.provider
            for persisted_turn in (
                store_mappers.turn_record_to_runtime(record)
                for record in queries.list_turns_for_thread(connection, thread.thread_id)
            )
            if persisted_turn.execution_options.provider
        }
        if (
            requested_provider
            and historical_providers
            and historical_providers != {requested_provider}
            and _thread_has_provider_native_history(items)
        ):
            providers = ", ".join(sorted(historical_providers))
            raise ValueError(
                "Cross-provider replay is not supported for threads with provider-native history. "
                f"Requested provider={requested_provider!r}, historical providers={providers}."
            )
        next_ordinal = 1 if latest_model_call is None else latest_model_call.ordinal + 1
        LOGGER.info(
            "Assembling context for assistant turn %s thread=%s item_count=%s next_model_call_ordinal=%s",
            turn.turn_id,
            thread.thread_id,
            len(items),
            next_ordinal,
        )
        request = ModelInvocationRequest(
            thread_id=thread.thread_id,
            turn_id=turn.turn_id,
            model_call_id=AgentModelCall(
                thread_id=thread.thread_id,
                turn_id=turn.turn_id,
                ordinal=next_ordinal,
            ).model_call_id,
            provider=requested_provider,
            model=turn.execution_options.model or agent_spec.default_model,
            instructions=agent_spec.instructions,
            items=items,
            local_tools=agent_spec.local_tools,
            hosted_tools=agent_spec.hosted_tools,
            continuity_mode=turn.execution_options.continuity_mode,
            continuation={},
            provider_extras=dict(turn.execution_options.provider_extras),
            reasoning_effort=turn.execution_options.reasoning_effort,
            metadata={"agent_id": agent_spec.agent_id},
        )
        model_call = AgentModelCall(
            model_call_id=request.model_call_id,
            thread_id=request.thread_id,
            turn_id=request.turn_id,
            ordinal=next_ordinal,
            provider=request.provider,
            model=request.model,
            status="created",
            agent_spec_snapshot=agent_spec.model_dump(mode="json"),
            request_payload=request.model_dump(mode="json"),
        )
        updated_turn = turn.model_copy(
            update={
                "status": "active",
                "phase": "executing_model",
            }
        )
        turn_record, model_call_record = commands.begin_model_call(
            connection,
            turn=store_mappers.turn_record_from_runtime(updated_turn),
            model_call=store_mappers.model_call_record_from_runtime(model_call),
        )
        persisted_turn = store_mappers.turn_record_to_runtime(turn_record)
        persisted_model_call = store_mappers.model_call_record_to_runtime(model_call_record)
        LOGGER.info(
            "Created model call %s for assistant turn %s provider=%s model=%s",
            persisted_model_call.model_call_id,
            persisted_turn.turn_id,
            request.provider,
            request.model,
        )
        self._emit(
            RuntimeEventType.MODEL_CALL_CREATED,
            worker_id=worker_id,
            thread_id=thread.thread_id,
            turn_id=persisted_turn.turn_id,
            model_call_id=persisted_model_call.model_call_id,
            payload=ModelCallCreatedPayload(
                provider=request.provider,
                model=request.model,
                ordinal=next_ordinal,
            ),
        )
        self._emit(
            RuntimeEventType.TURN_PHASE_CHANGED,
            worker_id=worker_id,
            thread_id=thread.thread_id,
            turn_id=persisted_turn.turn_id,
            payload=TurnPhaseChangedPayload(phase=persisted_turn.phase, status=persisted_turn.status),
        )
        return persisted_turn

    def _handle_executing_model(
        self,
        connection: sqlite3.Connection,
        thread: AgentThread,
        turn: AssistantTurn,
        *,
        worker_id: str,
        db: SqliteDb,
    ) -> AssistantTurn:
        model_call_record = queries.get_latest_model_call(connection, turn.turn_id)
        if model_call_record is None:
            raise ValueError(f"Missing model call for assistant turn: {turn.turn_id}")
        model_call = store_mappers.model_call_record_to_runtime(model_call_record)
        claimed_model_call_record = commands.claim_model_call(
            connection,
            store_mappers.model_call_record_from_runtime(model_call),
            worker_id=worker_id,
            heartbeat_at=_now(),
            stale_before=_now() - timedelta(seconds=self.model_call_heartbeat_timeout_seconds),
        )
        if claimed_model_call_record is not None:
            model_call = store_mappers.model_call_record_to_runtime(claimed_model_call_record)
        if model_call.status != "running":
            LOGGER.info(
                "Skipping assistant turn %s because model call %s could not be claimed",
                turn.turn_id,
                model_call.model_call_id,
            )
            return turn
        request = ModelInvocationRequest.model_validate(model_call.request_payload)
        LOGGER.info(
            "Invoking model for assistant turn %s model_call=%s provider=%s model=%s",
            turn.turn_id,
            model_call.model_call_id,
            request.provider,
            request.model,
        )
        self._emit(
            RuntimeEventType.MODEL_CALL_STARTED,
            worker_id=worker_id,
            thread_id=thread.thread_id,
            turn_id=turn.turn_id,
            model_call_id=model_call.model_call_id,
            payload=ModelCallStartedPayload(provider=request.provider, model=request.model),
        )
        try:
            with background_heartbeat(
                interval_seconds=self.model_call_heartbeat_interval_seconds,
                callback=self._build_subaction_heartbeat_updater(
                    db,
                    model_call_id=model_call.model_call_id,
                ),
            ):
                result = self.executor.invoke(request)
        except Exception as error:
            LOGGER.exception(
                "Model execution failed for assistant turn %s model_call=%s",
                turn.turn_id,
                model_call.model_call_id,
            )
            failed_model_call = model_call.model_copy(
                update={
                    "status": "failed",
                    "error": {"message": str(error)},
                    "heartbeat_at": None,
                    "completed_at": _now(),
                }
            )
            failed_turn = turn.model_copy(
                update={
                    "status": "active",
                    "phase": "failed",
                    "error": {"message": str(error)},
                }
            )
            turn_record, _ = commands.complete_model_call_failure(
                connection,
                turn=store_mappers.turn_record_from_runtime(failed_turn),
                model_call=store_mappers.model_call_record_from_runtime(failed_model_call),
            )
            persisted_turn = store_mappers.turn_record_to_runtime(turn_record)
            self._emit(
                RuntimeEventType.MODEL_CALL_FAILED,
                worker_id=worker_id,
                thread_id=thread.thread_id,
                turn_id=persisted_turn.turn_id,
                model_call_id=model_call.model_call_id,
                payload=ErrorPayload(error=str(error)),
            )
            self._emit(
                RuntimeEventType.TURN_PHASE_CHANGED,
                worker_id=worker_id,
                thread_id=thread.thread_id,
                turn_id=persisted_turn.turn_id,
                payload=TurnPhaseChangedPayload(phase=persisted_turn.phase, status=persisted_turn.status),
            )
            return persisted_turn

        completed_model_call = model_call.model_copy(
            update={
                "status": "completed",
                "response_payload": result.raw_response,
                "usage": result.usage,
                "provider_request_id": result.provider_request_id,
                "provider_response_id": result.provider_response_id,
                "heartbeat_at": None,
                "completed_at": _now(),
            }
        )
        updated_usage = _merge_usage(turn.usage, result.usage)
        turn_updates = {
            "usage": updated_usage,
            "provider_response_id": result.provider_response_id or turn.provider_response_id,
            "provider_conversation_id": result.provider_conversation_id or turn.provider_conversation_id,
        }
        invocations: list[ToolInvocation] = []
        if result.tool_requests:
            invocation_map = {request.item_id: request for request in result.tool_requests}
            for item in result.output_items:
                if item.item_type != "tool_call":
                    continue
                request_item = invocation_map.get(item.item_id)
                if request_item is None:
                    continue
                invocations.append(
                    ToolInvocation(
                        thread_id=thread.thread_id,
                        turn_id=turn.turn_id,
                        model_call_id=completed_model_call.model_call_id,
                        tool_call_item_id=item.item_id,
                        tool_name=request_item.tool_name,
                        arguments=request_item.arguments,
                        status="requested",
                    )
                )
            next_turn = turn.model_copy(update={**turn_updates, "phase": "executing_tools"})
        else:
            next_turn = turn.model_copy(update={**turn_updates, "phase": "completed"})

        turn_record, model_call_record, persisted_item_records = commands.complete_model_call_success(
            connection,
            turn=store_mappers.turn_record_from_runtime(next_turn),
            model_call=store_mappers.model_call_record_from_runtime(completed_model_call),
            output_items=[store_mappers.item_record_from_runtime(item) for item in result.output_items],
            tool_invocations=[
                store_mappers.tool_invocation_record_from_runtime(invocation)
                for invocation in invocations
            ],
        )
        persisted_turn = store_mappers.turn_record_to_runtime(turn_record)
        persisted_model_call = store_mappers.model_call_record_to_runtime(model_call_record)
        persisted_items = [
            store_mappers.item_record_to_runtime(record) for record in persisted_item_records
        ]
        LOGGER.info(
            "Model call completed turn=%s model_call=%s output_items=%s tool_requests=%s finish_reason=%s",
            persisted_turn.turn_id,
            persisted_model_call.model_call_id,
            len(persisted_items),
            len(result.tool_requests),
            result.finish_reason,
        )
        if invocations:
            LOGGER.info(
                "Assistant turn %s queued %s tool invocations after model call %s",
                persisted_turn.turn_id,
                len(invocations),
                persisted_model_call.model_call_id,
            )
        else:
            LOGGER.info(
                "Assistant turn %s has no tool requests; transitioning to completed",
                persisted_turn.turn_id,
            )
        self._emit(
            RuntimeEventType.MODEL_CALL_COMPLETED,
            worker_id=worker_id,
            thread_id=thread.thread_id,
            turn_id=persisted_turn.turn_id,
            model_call_id=persisted_model_call.model_call_id,
            payload=ModelCallCompletedPayload(
                finish_reason=result.finish_reason,
                tool_requests=len(result.tool_requests),
                output_items=len(persisted_items),
            ),
        )
        self._emit(
            RuntimeEventType.TURN_PHASE_CHANGED,
            worker_id=worker_id,
            thread_id=thread.thread_id,
            turn_id=persisted_turn.turn_id,
            payload=TurnPhaseChangedPayload(phase=persisted_turn.phase, status=persisted_turn.status),
        )
        return persisted_turn

    def _handle_executing_tools(
        self,
        connection: sqlite3.Connection,
        thread: AgentThread,
        turn: AssistantTurn,
        *,
        worker_id: str,
        db: SqliteDb,
    ) -> AssistantTurn:
        invocations = [
            store_mappers.tool_invocation_record_to_runtime(record)
            for record in queries.list_pending_tool_invocations(connection, turn.turn_id)
        ]
        if not invocations:
            LOGGER.info(
                "Assistant turn %s has no pending tool invocations; transitioning back to assembling_context",
                turn.turn_id,
            )
            updated_turn = turn.model_copy(update={"phase": "assembling_context"})
            persisted_turn = store_mappers.turn_record_to_runtime(
                commands.update_turn(
                    connection,
                    store_mappers.turn_record_from_runtime(updated_turn),
                )
            )
            self._emit(
                RuntimeEventType.TURN_PHASE_CHANGED,
                worker_id=worker_id,
                thread_id=thread.thread_id,
                turn_id=persisted_turn.turn_id,
                payload=TurnPhaseChangedPayload(phase=persisted_turn.phase, status=persisted_turn.status),
            )
            return persisted_turn

        any_completed = False
        LOGGER.info("Executing %s tool invocations for assistant turn %s", len(invocations), turn.turn_id)
        for invocation in invocations:
            claimed_record = commands.claim_tool_invocation(
                connection,
                store_mappers.tool_invocation_record_from_runtime(invocation),
                worker_id=worker_id,
                heartbeat_at=_now(),
                stale_before=_now()
                - timedelta(seconds=self.tool_invocation_heartbeat_timeout_seconds),
            )
            if claimed_record is None:
                continue
            running_invocation = store_mappers.tool_invocation_record_to_runtime(claimed_record)
            LOGGER.info(
                "Running tool invocation %s turn=%s tool=%s",
                running_invocation.tool_invocation_id,
                turn.turn_id,
                running_invocation.tool_name,
            )
            self._emit(
                RuntimeEventType.TOOL_INVOCATION_STARTED,
                worker_id=worker_id,
                thread_id=thread.thread_id,
                turn_id=turn.turn_id,
                tool_invocation_id=running_invocation.tool_invocation_id,
                payload=ToolInvocationStartedPayload(tool_name=running_invocation.tool_name),
            )
            with background_heartbeat(
                interval_seconds=self.tool_invocation_heartbeat_interval_seconds,
                callback=self._build_subaction_heartbeat_updater(
                    db,
                    tool_invocation_id=running_invocation.tool_invocation_id,
                ),
            ):
                result = self.tools.execute(
                    self.tool_context,
                    ToolCallRequest(
                        tool_name=running_invocation.tool_name,
                        arguments=running_invocation.arguments,
                        item_id=running_invocation.tool_call_item_id,
                    )
                )
            item = AgentItem(
                thread_id=thread.thread_id,
                turn_id=turn.turn_id,
                model_call_id=running_invocation.model_call_id,
                parent_item_id=running_invocation.tool_call_item_id,
                item_type="tool_result",
                role="tool",
                name=running_invocation.tool_name,
                content_text=None,
                result=result.result,
                metadata={
                    "tool_call_id": running_invocation.tool_call_item_id,
                    "status": result.status,
                    "error_text": result.error_text,
                },
            )
            completed_invocation = running_invocation.model_copy(
                update={
                    "result": result.result,
                    "status": result.status,
                    "error_text": result.error_text,
                    "worker_id": None,
                    "heartbeat_at": None,
                    "completed_at": _now(),
                }
            )
            completed_record, persisted_item_record = commands.complete_tool_invocation(
                connection,
                invocation=store_mappers.tool_invocation_record_from_runtime(completed_invocation),
                result_item=store_mappers.item_record_from_runtime(item),
            )
            completed_invocation = store_mappers.tool_invocation_record_to_runtime(completed_record)
            persisted_item = store_mappers.item_record_to_runtime(persisted_item_record)
            LOGGER.info(
                "Tool invocation completed %s turn=%s tool=%s status=%s",
                completed_invocation.tool_invocation_id,
                turn.turn_id,
                completed_invocation.tool_name,
                result.status,
            )
            self._emit(
                RuntimeEventType.TOOL_INVOCATION_COMPLETED
                if result.status == "completed"
                else RuntimeEventType.TOOL_INVOCATION_FAILED,
                worker_id=worker_id,
                thread_id=thread.thread_id,
                turn_id=turn.turn_id,
                tool_invocation_id=completed_invocation.tool_invocation_id,
                payload=ToolInvocationCompletedPayload(
                    tool_name=completed_invocation.tool_name,
                    status=result.status,
                    error_text=result.error_text,
                    result_item_id=persisted_item.item_id,
                ),
            )
            any_completed = True

        if any_completed:
            LOGGER.info(
                "Assistant turn %s completed tool batch; transitioning to assembling_context",
                turn.turn_id,
            )
            updated_turn = turn.model_copy(update={"phase": "assembling_context"})
            persisted_turn = store_mappers.turn_record_to_runtime(
                commands.update_turn(
                    connection,
                    store_mappers.turn_record_from_runtime(updated_turn),
                )
            )
            self._emit(
                RuntimeEventType.TURN_PHASE_CHANGED,
                worker_id=worker_id,
                thread_id=thread.thread_id,
                turn_id=persisted_turn.turn_id,
                payload=TurnPhaseChangedPayload(phase=persisted_turn.phase, status=persisted_turn.status),
            )
            return persisted_turn
        return turn

    def _build_tool_invocation_heartbeat_updater(
        self,
        db: SqliteDb,
        tool_invocation_id: str,
    ):
        """Return a callback that refreshes one running tool invocation heartbeat."""

        def _update() -> None:
            with db.connect() as heartbeat_connection:
                commands.update_tool_invocation_heartbeat(
                    heartbeat_connection,
                    tool_invocation_id=tool_invocation_id,
                    heartbeat_at=_now(),
                )
                heartbeat_connection.commit()

        return _update

    def _build_model_call_heartbeat_updater(
        self,
        db: SqliteDb,
        model_call_id: str,
    ):
        """Return a callback that refreshes one running model-call heartbeat."""

        def _update() -> None:
            with db.connect() as heartbeat_connection:
                commands.update_model_call_heartbeat(
                    heartbeat_connection,
                    model_call_id=model_call_id,
                    heartbeat_at=_now(),
                )
                heartbeat_connection.commit()

        return _update

    def _build_turn_heartbeat_updater(
        self,
        db: SqliteDb,
        turn_id: str,
        *,
        worker_id: str,
    ):
        """Return a callback that refreshes one running assistant-turn heartbeat."""

        def _update() -> None:
            with db.connect() as heartbeat_connection:
                commands.update_turn_heartbeat(
                    heartbeat_connection,
                    turn_id=turn_id,
                    worker_id=worker_id,
                    heartbeat_at=_now(),
                )
                heartbeat_connection.commit()

        return _update

    def _build_subaction_heartbeat_updater(
        self,
        db: SqliteDb,
        *,
        model_call_id: str | None = None,
        tool_invocation_id: str | None = None,
    ):
        """Return a callback that refreshes the active model/tool sub-action heartbeat."""

        model_update = (
            None
            if model_call_id is None
            else self._build_model_call_heartbeat_updater(db, model_call_id)
        )
        tool_update = (
            None
            if tool_invocation_id is None
            else self._build_tool_invocation_heartbeat_updater(
                db,
                tool_invocation_id,
            )
        )

        def _update() -> None:
            if model_update is not None:
                model_update()
            if tool_update is not None:
                tool_update()

        return _update

    def _handle_completed(
        self,
        connection: sqlite3.Connection,
        thread: AgentThread,
        turn: AssistantTurn,
        *,
        worker_id: str,
    ) -> AssistantTurn:
        LOGGER.info("Assistant turn %s transitioning to completed", turn.turn_id)
        updated_thread = thread.model_copy(
            update={
                "status": "active",
                "phase": "idle",
                "active_turn_id": None,
                "last_turn_id": turn.turn_id,
            }
        )
        updated_turn = turn.model_copy(update={"status": "completed", "completed_at": turn.completed_at or _now()})
        updated_turn = updated_turn.model_copy(
            update={
                "claim_worker_id": None,
                "heartbeat_at": None,
            }
        )
        _thread_record, turn_record = commands.finalize_turn_completed(
            connection,
            thread=store_mappers.thread_record_from_runtime(updated_thread),
            turn=store_mappers.turn_record_from_runtime(updated_turn),
        )
        persisted_turn = store_mappers.turn_record_to_runtime(turn_record)
        self._emit(
            RuntimeEventType.TURN_COMPLETED,
            worker_id=worker_id,
            thread_id=thread.thread_id,
            turn_id=persisted_turn.turn_id,
            payload=TurnTerminalPayload(status=persisted_turn.status, phase=persisted_turn.phase),
        )
        return persisted_turn

    def _handle_failed(
        self,
        connection: sqlite3.Connection,
        thread: AgentThread,
        turn: AssistantTurn,
        *,
        worker_id: str,
    ) -> AssistantTurn:
        LOGGER.info("Assistant turn %s transitioning to failed error=%s", turn.turn_id, turn.error)
        updated_thread = thread.model_copy(
            update={
                "status": "active",
                "phase": "idle",
                "active_turn_id": None,
                "last_turn_id": turn.turn_id,
            }
        )
        updated_turn = turn.model_copy(update={"status": "failed", "completed_at": turn.completed_at or _now()})
        updated_turn = updated_turn.model_copy(
            update={
                "claim_worker_id": None,
                "heartbeat_at": None,
            }
        )
        _thread_record, turn_record = commands.finalize_turn_failed(
            connection,
            thread=store_mappers.thread_record_from_runtime(updated_thread),
            turn=store_mappers.turn_record_from_runtime(updated_turn),
        )
        persisted_turn = store_mappers.turn_record_to_runtime(turn_record)
        self._emit(
            RuntimeEventType.TURN_FAILED,
            worker_id=worker_id,
            thread_id=thread.thread_id,
            turn_id=persisted_turn.turn_id,
            payload=TurnFailedPayload(
                status=persisted_turn.status,
                phase=persisted_turn.phase,
                error=turn.error,
            ),
        )
        return persisted_turn
