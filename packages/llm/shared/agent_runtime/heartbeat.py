from __future__ import annotations

import logging
import sqlite3
import threading
from collections.abc import Callable
from contextlib import contextmanager
from typing import Iterator

HeartbeatCallback = Callable[[], None]
LOGGER = logging.getLogger(__name__)


def _is_benign_sqlite_lock(error: Exception) -> bool:
    """Return True for transient SQLite lock contention during advisory heartbeats."""
    return isinstance(error, sqlite3.OperationalError) and "database is locked" in str(error).lower()


@contextmanager
def background_heartbeat(
    *,
    interval_seconds: float,
    callback: HeartbeatCallback,
) -> Iterator[None]:
    """Run a callback on a fixed interval in a background thread for one scope."""
    stop_event = threading.Event()

    def _run() -> None:
        while not stop_event.wait(interval_seconds):
            try:
                callback()
            except Exception as error:  # noqa: BLE001
                if _is_benign_sqlite_lock(error):
                    LOGGER.debug("Heartbeat callback skipped due to transient SQLite lock contention")
                    continue
                LOGGER.exception("Heartbeat callback failed")

    thread = threading.Thread(target=_run, daemon=True, name="agent-runtime-heartbeat")
    thread.start()
    try:
        yield
    finally:
        stop_event.set()
        thread.join(timeout=max(interval_seconds, 1.0))
