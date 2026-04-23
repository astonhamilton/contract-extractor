from __future__ import annotations

from pathlib import Path

from fastapi import Depends, Request

from packages.data_store.connect import SqliteDb, default_db
from packages.llm.shared.agent_runtime.embedded_service import EmbeddedAgentRuntimeService
from packages.llm.shared.agent_runtime.event_bus import InMemoryRuntimeEventBus


def get_repo_root() -> Path:
    """Return the repository root for API dependency wiring."""

    return Path(__file__).resolve().parents[2]


def get_contract_intelligence_db(repo_root: Path = Depends(get_repo_root)) -> SqliteDb:
    """Return the contract-intelligence DB handle."""

    return default_db(repo_root)


def get_embedded_agent_runtime_service(request: Request) -> EmbeddedAgentRuntimeService:
    """Return the API-owned embedded agent runtime service."""
    return request.app.state.agent_runtime_service


def get_agent_runtime_db(repo_root: Path = Depends(get_repo_root)) -> SqliteDb:
    """Return the agent-runtime DB handle."""

    return default_db(repo_root)


def get_embedded_agent_runtime_event_bus(
    service: EmbeddedAgentRuntimeService = Depends(get_embedded_agent_runtime_service),
) -> InMemoryRuntimeEventBus:
    """Return the shared in-memory runtime event bus for same-process subscribers."""
    return service.event_bus
