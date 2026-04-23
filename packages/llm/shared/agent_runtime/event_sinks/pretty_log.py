from __future__ import annotations

from packages.llm.shared.agent_runtime.events import RuntimeEvent


class PrettyPrintRuntimeEventSink:
    """Print compact human-readable runtime event lines."""

    def emit(self, event: RuntimeEvent) -> None:
        """Print one concise formatted event line."""
        timestamp = event.occurred_at.astimezone().strftime("%H:%M:%S")
        scopes = []
        if event.thread_id:
            scopes.append(f"thread={event.thread_id}")
        if event.turn_id:
            scopes.append(f"turn={event.turn_id}")
        if event.model_call_id:
            scopes.append(f"model_call={event.model_call_id}")
        if event.tool_invocation_id:
            scopes.append(f"tool={event.tool_invocation_id}")
        if event.worker_id:
            scopes.append(f"worker={event.worker_id}")
        payload_summary = " ".join(
            f"{key}={value}" for key, value in event.payload.items() if value is not None
        )
        scope_text = " ".join(scopes)
        line = f"[{timestamp}] {event.event_type}"
        if scope_text:
            line += f"  {scope_text}"
        if payload_summary:
            line += f"  {payload_summary}"
        print(line, flush=True)

