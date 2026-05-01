from __future__ import annotations

from pathlib import Path

from fastapi import Depends, HTTPException, Request

from apps.api.auth import auth_users_path, session_user_key
from packages.app_services.auth.models import AuthenticatedUser
from packages.app_services.auth.session import resolve_authenticated_user
from packages.data_store.connect import SqliteDb, default_db
from packages.llm.shared.agent_runtime.embedded_service import EmbeddedAgentRuntimeService
from packages.llm.shared.agent_runtime.event_bus import InMemoryRuntimeEventBus

REPO_ROOT = Path(__file__).resolve().parents[2]


def get_repo_root() -> Path:
    """Return the repository root for API dependency wiring."""

    return REPO_ROOT


def get_auth_users_path() -> Path:
    """Return the runtime JSON user-store path."""

    return auth_users_path(REPO_ROOT)


def get_contract_intelligence_db() -> SqliteDb:
    """Return the contract-intelligence DB handle."""

    return default_db(REPO_ROOT)


def get_embedded_agent_runtime_service(request: Request) -> EmbeddedAgentRuntimeService:
    """Return the API-owned embedded agent runtime service."""
    return request.app.state.agent_runtime_service


def get_agent_runtime_db() -> SqliteDb:
    """Return the agent-runtime DB handle."""

    return default_db(REPO_ROOT)


def get_embedded_agent_runtime_event_bus(
    service: EmbeddedAgentRuntimeService = Depends(get_embedded_agent_runtime_service),
) -> InMemoryRuntimeEventBus:
    """Return the shared in-memory runtime event bus for same-process subscribers."""
    return service.event_bus


def get_authenticated_user_optional(
    request: Request,
    users_path: Path = Depends(get_auth_users_path),
) -> AuthenticatedUser | None:
    """Return the authenticated user for the current signed session, if any."""

    if hasattr(request.state, "authenticated_user"):
        return request.state.authenticated_user
    user_key = session_user_key(request.session)
    user = resolve_authenticated_user(users_path, user_key=user_key)
    request.state.authenticated_user = user
    return user


def require_authenticated_user(
    user: AuthenticatedUser | None = Depends(get_authenticated_user_optional),
) -> AuthenticatedUser:
    """Require one authenticated session user for a protected route."""

    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user
