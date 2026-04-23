"""Shared assistant/agent runtime package.

This package intentionally uses lazy re-exports.

Why:
- Several lower-level runtime and data-store modules import specific runtime
  submodules such as `packages.llm.shared.agent_runtime.models`.
- Python loads the package `__init__` before loading submodules.
- Eagerly importing the full runtime surface here creates circular-import paths
  between:
  - data-store models/common
  - runtime models
  - runtime loop/worker
  - package-level re-exports

Using `__getattr__` keeps the convenience re-export surface for callers that do
`from packages.llm.shared.agent_runtime import ...` while avoiding import-time
cycles for callers that only need a specific submodule.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AgentRegistry",
    "AgentRuntimeWorker",
    "CompositeRuntimeEventEmitter",
    "EmbeddedAgentRuntimeService",
    "InMemoryRuntimeEventBus",
    "NullRuntimeEventEmitter",
    "RuntimeEvent",
    "RuntimeEventEmitter",
    "WaitedThreadResult",
    "WaitedTurnResult",
    "WorkerPassResult",
    "build_embedded_agent_runtime_service",
    "openai_image_generation",
    "openai_web_search_preview",
    "send_input_and_wait",
    "start_task_and_wait",
    "start_thread_and_wait",
    "wait_for_thread_idle",
    "wait_for_turn",
]

_EXPORTS: dict[str, tuple[str, str]] = {
    "EmbeddedAgentRuntimeService": (
        "packages.llm.shared.agent_runtime.embedded_service",
        "EmbeddedAgentRuntimeService",
    ),
    "build_embedded_agent_runtime_service": (
        "packages.llm.shared.agent_runtime.embedded_service",
        "build_embedded_agent_runtime_service",
    ),
    "InMemoryRuntimeEventBus": (
        "packages.llm.shared.agent_runtime.event_bus",
        "InMemoryRuntimeEventBus",
    ),
    "CompositeRuntimeEventEmitter": (
        "packages.llm.shared.agent_runtime.emitter",
        "CompositeRuntimeEventEmitter",
    ),
    "NullRuntimeEventEmitter": (
        "packages.llm.shared.agent_runtime.emitter",
        "NullRuntimeEventEmitter",
    ),
    "RuntimeEventEmitter": (
        "packages.llm.shared.agent_runtime.emitter",
        "RuntimeEventEmitter",
    ),
    "RuntimeEvent": (
        "packages.llm.shared.agent_runtime.events",
        "RuntimeEvent",
    ),
    "openai_image_generation": (
        "packages.llm.shared.agent_runtime.hosted_tools",
        "openai_image_generation",
    ),
    "openai_web_search_preview": (
        "packages.llm.shared.agent_runtime.hosted_tools",
        "openai_web_search_preview",
    ),
    "AgentRegistry": (
        "packages.llm.shared.agent_runtime.registry",
        "AgentRegistry",
    ),
    "WaitedThreadResult": (
        "packages.llm.shared.agent_runtime.waiter",
        "WaitedThreadResult",
    ),
    "WaitedTurnResult": (
        "packages.llm.shared.agent_runtime.waiter",
        "WaitedTurnResult",
    ),
    "send_input_and_wait": (
        "packages.llm.shared.agent_runtime.waiter",
        "send_input_and_wait",
    ),
    "start_task_and_wait": (
        "packages.llm.shared.agent_runtime.waiter",
        "start_task_and_wait",
    ),
    "start_thread_and_wait": (
        "packages.llm.shared.agent_runtime.waiter",
        "start_thread_and_wait",
    ),
    "wait_for_thread_idle": (
        "packages.llm.shared.agent_runtime.waiter",
        "wait_for_thread_idle",
    ),
    "wait_for_turn": (
        "packages.llm.shared.agent_runtime.waiter",
        "wait_for_turn",
    ),
    "AgentRuntimeWorker": (
        "packages.llm.shared.agent_runtime.worker",
        "AgentRuntimeWorker",
    ),
    "WorkerPassResult": (
        "packages.llm.shared.agent_runtime.worker",
        "WorkerPassResult",
    ),
}


def __getattr__(name: str) -> Any:
    """Resolve package-level convenience exports lazily."""

    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
