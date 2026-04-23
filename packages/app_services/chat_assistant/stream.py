"""Thread-stream application service.

This module defines the semantic streaming protocol for `GET /threads/{id}/stream`.

Design:
- The database is the source of truth for all replay and recovery decisions.
- The in-memory runtime event bus is only a low-latency wake-up signal.
- Transport owns SSE framing and connection management.
- This module owns thread-stream semantics:
  - initial snapshot behavior
  - cursor-based replay behavior
  - reset behavior when a client cursor is invalid
  - display-shaped item mapping for streamed payloads

Protocol overview:
- The stream is cursor-based.
- The cursor is the highest `asst_items.seq` the client has fully applied.
- A client can connect with no cursor for a cold start, or with a prior cursor
  to resume after reconnect.
- The service emits one of four semantic event types:
  - `snapshot`
    - full thread shell plus the full current item timeline
    - used for first load
  - `items_appended`
    - thread shell plus only the items after a valid cursor
    - used for normal incremental progress
  - `thread_updated`
    - thread shell changed but no new items were appended
    - used for title/status/phase metadata changes
  - `heartbeat`
    - no state change; keeps the connection warm and confirms the current cursor
  - `reset`
    - instructs the client to replace its local state with the included full
      snapshot because the supplied cursor cannot be trusted for replay

Replay rules:
- If no cursor is supplied:
  - emit `snapshot`
- If a cursor is supplied and it is <= current max item sequence:
  - emit `items_appended` with all items strictly after that cursor
  - or emit nothing if there are no missing items
- If a cursor is supplied and it is > current max item sequence:
  - emit `reset` with a fresh full snapshot

Why reset when the cursor is ahead?
- A cursor ahead of the database means the server cannot safely infer the
  client's state. This can happen with tab bugs, stale local state, or future
  retention/truncation policies. The correct recovery is a full replacement.

Client application model:
- `snapshot` and `reset` are full replacement events.
- `items_appended` is an append-only incremental event.
- `thread_updated` replaces only the local thread shell metadata.
- `heartbeat` changes nothing except confirming the stream is alive.

This service intentionally does not know about SSE frame formatting, HTTP
headers, EventSource reconnection, or `Last-Event-ID`. Transport adapts those
mechanics onto these semantic events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from packages.app_services.chat_assistant.items import ThreadItemView, thread_item_view_from_item
from packages.app_services.chat_assistant.models import ThreadDetail
from packages.app_services.chat_assistant.thread_detail import get_thread_detail
from packages.data_store.connect import SqliteDb
from packages.data_store.llm_agent_runtime.queries.items import list_items, list_items_after, max_item_seq
from packages.schemas.common import BaseSchema


class ThreadStreamSnapshotPayload(BaseSchema):
    """Full thread state used to initialize or replace a client's local state."""

    thread: ThreadDetail
    items: list[ThreadItemView]


class ThreadStreamItemsAppendedPayload(BaseSchema):
    """Incremental append payload containing only items after a valid cursor."""

    thread: ThreadDetail
    items: list[ThreadItemView]


class ThreadStreamThreadUpdatedPayload(BaseSchema):
    """Thread shell update payload with no accompanying item changes."""

    thread: ThreadDetail


class ThreadStreamResetPayload(BaseSchema):
    """Full replacement payload used when cursor replay is no longer trustworthy."""

    reason: str
    thread: ThreadDetail
    items: list[ThreadItemView]


class ThreadStreamHeartbeatPayload(BaseSchema):
    """Keepalive payload confirming the stream is still active at one cursor."""

    status: str = "ok"


class ThreadStreamEnvelope(BaseSchema):
    """Semantic thread-stream event before transport-specific framing.

    Fields:
    - `protocol_version`
      - integer protocol version for forward-compatible clients
    - `type`
      - semantic event name (`snapshot`, `items_appended`, `thread_updated`, `heartbeat`, `reset`)
    - `thread_id`
      - thread the event applies to
    - `cursor`
      - highest fully-applied item sequence after processing this event
    - `sent_at`
      - server timestamp for observability/debugging
    - `payload`
      - event-specific structured body

    Consumers should treat `cursor` as authoritative. The SSE transport layer may
    also mirror it into the SSE `id:` field so reconnects can resume from
    `Last-Event-ID`, but that is a transport concern, not part of the semantic
    contract this model represents.
    """

    protocol_version: int = 1
    type: Literal["snapshot", "items_appended", "thread_updated", "heartbeat", "reset"]
    thread_id: str
    cursor: int
    sent_at: str
    payload: dict[str, object]


def _sent_at() -> str:
    return datetime.now(UTC).isoformat()


def _snapshot_payload_from_connection(
    db: SqliteDb,
    *,
    thread_id: str,
) -> ThreadStreamSnapshotPayload | None:
    """Return the full current thread state for one snapshot-like event."""
    with db.connect() as connection:
        thread = get_thread_detail(db, thread_id=thread_id)
        if thread is None:
            return None
        items = [thread_item_view_from_item(item) for item in list_items(connection, thread_id)]
        return ThreadStreamSnapshotPayload(
            thread=thread,
            items=items,
        )


def build_initial_thread_stream_event(
    db: SqliteDb,
    *,
    thread_id: str,
    after_cursor: int | None,
) -> ThreadStreamEnvelope | None:
    """Return the initial stream event for one connect/reconnect attempt.

    Rules:
    - `after_cursor is None` -> full `snapshot`
    - `after_cursor > current max seq` -> `reset`
    - valid cursor with missing items -> `items_appended`
    - valid cursor with no missing items -> no initial event
    """
    with db.connect() as connection:
        latest_cursor = max_item_seq(connection, thread_id)
    if after_cursor is None:
        payload = _snapshot_payload_from_connection(db, thread_id=thread_id)
        if payload is None:
            return None
        snapshot_cursor = payload.items[-1].record.seq if payload.items else 0
        return ThreadStreamEnvelope(
            type="snapshot",
            thread_id=thread_id,
            cursor=snapshot_cursor,
            sent_at=_sent_at(),
            payload=payload.model_dump(mode="json"),
        )

    if after_cursor > latest_cursor:
        payload = _snapshot_payload_from_connection(db, thread_id=thread_id)
        if payload is None:
            return None
        reset_payload = ThreadStreamResetPayload(
            reason="cursor_out_of_range",
            thread=payload.thread,
            items=payload.items,
        )
        reset_cursor = payload.items[-1].record.seq if payload.items else 0
        return ThreadStreamEnvelope(
            type="reset",
            thread_id=thread_id,
            cursor=reset_cursor,
            sent_at=_sent_at(),
            payload=reset_payload.model_dump(mode="json"),
        )

    with db.connect() as connection:
        appended_items = list_items_after(connection, thread_id, after_seq=after_cursor)
    thread = get_thread_detail(db, thread_id=thread_id)
    if thread is None:
        return None
    if not appended_items:
        payload = ThreadStreamThreadUpdatedPayload(thread=thread)
        return ThreadStreamEnvelope(
            type="thread_updated",
            thread_id=thread_id,
            cursor=after_cursor,
            sent_at=_sent_at(),
            payload=payload.model_dump(mode="json"),
        )
    payload = ThreadStreamItemsAppendedPayload(
        thread=thread,
        items=[thread_item_view_from_item(item) for item in appended_items],
    )
    append_cursor = payload.items[-1].record.seq if payload.items else after_cursor
    return ThreadStreamEnvelope(
        type="items_appended",
        thread_id=thread_id,
        cursor=append_cursor,
        sent_at=_sent_at(),
        payload=payload.model_dump(mode="json"),
    )


def build_incremental_thread_stream_event(
    db: SqliteDb,
    *,
    thread_id: str,
    after_cursor: int,
) -> ThreadStreamEnvelope | None:
    """Return one post-connect incremental event for a thread, if any.

    This is used after the SSE connection is already live. The same cursor rules
    apply as the initial connect path, except that normal no-op polls return
    `None` and the transport layer can emit a heartbeat instead.
    """

    return build_initial_thread_stream_event(
        db,
        thread_id=thread_id,
        after_cursor=after_cursor,
    )


def build_thread_stream_heartbeat(
    *,
    thread_id: str,
    cursor: int,
) -> ThreadStreamEnvelope:
    """Return one keepalive event for an otherwise idle connection."""

    return ThreadStreamEnvelope(
        type="heartbeat",
        thread_id=thread_id,
        cursor=cursor,
        sent_at=_sent_at(),
        payload=ThreadStreamHeartbeatPayload().model_dump(mode="json"),
    )
