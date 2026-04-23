from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse


def web_app_dist_dir(repo_root: Path) -> Path:
    """Return the deployed SPA artifact directory served by FastAPI."""

    return repo_root / "apps" / "api" / "static" / "web"


def web_app_index_path(repo_root: Path) -> Path:
    """Return the deployed SPA entrypoint file."""

    return web_app_dist_dir(repo_root) / "index.html"


def serve_web_app_index(repo_root: Path) -> FileResponse:
    """Return the deployed SPA entrypoint or a clear 404 when not deployed."""

    index_path = web_app_index_path(repo_root)
    if not index_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Frontend build not deployed. Run the web deploy script first.",
        )
    return FileResponse(index_path)
