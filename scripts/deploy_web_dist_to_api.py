from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIST_DIR = REPO_ROOT / "apps" / "web" / "dist"
TARGET_DIST_DIR = REPO_ROOT / "apps" / "api" / "static" / "web"


def deploy_web_dist() -> None:
    """Copy the built frontend artifact into the FastAPI static-serving location."""

    if not SOURCE_DIST_DIR.exists():
        raise SystemExit(
            "Web dist does not exist. Run `cd apps/web && npm run build` first."
        )
    if TARGET_DIST_DIR.exists():
        shutil.rmtree(TARGET_DIST_DIR)
    TARGET_DIST_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_DIST_DIR, TARGET_DIST_DIR)
    print(f"Deployed web dist to {TARGET_DIST_DIR}")


if __name__ == "__main__":
    deploy_web_dist()
