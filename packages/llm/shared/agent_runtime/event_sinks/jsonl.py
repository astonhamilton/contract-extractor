from __future__ import annotations

from pathlib import Path
from threading import Lock

from packages.llm.shared.agent_runtime.events import RuntimeEvent


class JsonlRuntimeEventSink:
    """Append structured runtime events to a JSONL file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: RuntimeEvent) -> None:
        """Append one event as a compact JSON line."""
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(event.model_dump_json() + "\n")
