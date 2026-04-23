from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from apps.api.settings import EmbeddedAgentRuntimeSettings
from packages.data_store.connect import SqliteDb
from packages.llm.agents.app.corpus_assistant.agent_spec import build_corpus_assistant_agent_spec
from packages.llm.agents.app.corpus_assistant.tool_registry import build_corpus_tool_registry
from packages.llm.shared.agent_runtime.embedded_service import (
    EmbeddedAgentRuntimeService,
    build_embedded_agent_runtime_service as build_shared_embedded_agent_runtime_service,
)
from packages.llm.shared.agent_runtime.emitter import CompositeRuntimeEventEmitter, RuntimeEventEmitter
from packages.llm.shared.agent_runtime.event_bus import InMemoryRuntimeEventBus
from packages.llm.shared.agent_runtime.event_sinks import (
    JsonlRuntimeEventSink,
    PrettyPrintRuntimeEventSink,
    PubSubRuntimeEventSink,
)
from packages.llm.shared.agent_runtime.litellm_executor import LiteLLMAgentExecutor
from packages.llm.shared.agent_runtime.registry import AgentRegistry
from packages.llm.shared.agent_runtime.tools import ToolExecutionContext
from packages.llm.agents.app.thread_titling import build_thread_titling_agent_spec


def default_agent_runtime_event_jsonl_path(repo_root: Path) -> Path:
    """Return the default JSONL event log path for the embedded API worker."""
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    return repo_root / ".logs" / "api" / "agent_runtime" / f"events_{timestamp}_pid{os.getpid()}.jsonl"


def build_embedded_event_emitter(
    *,
    repo_root: Path,
    bus: InMemoryRuntimeEventBus,
    enable_pretty: bool,
    enable_jsonl: bool,
) -> RuntimeEventEmitter:
    """Build the app-owned composite event emitter for the embedded worker."""
    sinks: list[RuntimeEventEmitter] = [PubSubRuntimeEventSink(bus)]
    if enable_pretty:
        sinks.append(PrettyPrintRuntimeEventSink())
    if enable_jsonl:
        sinks.append(JsonlRuntimeEventSink(default_agent_runtime_event_jsonl_path(repo_root)))
    return CompositeRuntimeEventEmitter(sinks)


def build_embedded_agent_runtime_service(
    *,
    repo_root: Path,
    db: SqliteDb,
) -> EmbeddedAgentRuntimeService:
    """Build the API-owned embedded worker service."""
    settings = EmbeddedAgentRuntimeSettings.from_env()
    event_bus = InMemoryRuntimeEventBus()
    event_emitter = build_embedded_event_emitter(
        repo_root=repo_root,
        bus=event_bus,
        enable_pretty=settings.event_pretty,
        enable_jsonl=settings.event_jsonl,
    )
    return build_shared_embedded_agent_runtime_service(
        db=db,
        agent_registry=AgentRegistry(
            [
                build_corpus_assistant_agent_spec,
                build_thread_titling_agent_spec,
            ]
        ),
        tools=build_corpus_tool_registry(),
        tool_context=ToolExecutionContext(
            db=db,
            repo_root=repo_root,
        ),
        executor=LiteLLMAgentExecutor(),
        event_bus=event_bus,
        event_emitter=event_emitter,
        enabled=settings.enabled,
        poll_interval_seconds=settings.poll_interval_seconds,
        max_turns=settings.max_turns,
        max_steps=settings.max_steps,
    )
