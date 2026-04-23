from __future__ import annotations

import asyncio
import json
from queue import Empty, Queue

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from apps.api.deps import (
    get_agent_runtime_db,
    get_embedded_agent_runtime_event_bus,
)
from apps.api.routes.thread_stream.schema import ThreadStreamEnvelopeResponse
from packages.app_services.chat_assistant.stream import (
    build_incremental_thread_stream_event,
    build_initial_thread_stream_event,
    build_thread_stream_heartbeat,
)
from packages.app_services.chat_assistant.thread_detail import get_thread_detail
from packages.data_store.connect import SqliteDb
from packages.llm.shared.agent_runtime.event_bus import InMemoryRuntimeEventBus

STREAM_RETRY_MS = 3000
STREAM_HEARTBEAT_SECONDS = 15.0
STREAM_DEBOUNCE_SECONDS = 0.10


def _cursor_from_request(*, request: Request, after_cursor: int | None) -> int | None:
    """Resolve the starting replay cursor from query or SSE reconnect headers.

    Priority:
    1. explicit `after_cursor` query param
    2. `Last-Event-ID` request header from automatic EventSource reconnect
    3. no cursor / cold start
    """

    if after_cursor is not None:
        return after_cursor
    last_event_id = request.headers.get("last-event-id")
    if not last_event_id:
        return None
    try:
        cursor = int(last_event_id)
    except ValueError:
        return None
    return cursor if cursor >= 0 else None


def _encode_sse(envelope: ThreadStreamEnvelopeResponse) -> str:
    """Return one SSE frame for a semantic thread-stream envelope."""

    payload = json.dumps(envelope.model_dump(mode="json"), separators=(",", ":"))
    return (
        f"retry: {STREAM_RETRY_MS}\n"
        f"id: {envelope.cursor}\n"
        f"event: {envelope.type}\n"
        f"data: {payload}\n\n"
    )


async def _thread_stream_iterator(
    *,
    request: Request,
    db: SqliteDb,
    bus: InMemoryRuntimeEventBus,
    thread_id: str,
    after_cursor: int | None,
):
    """Yield SSE frames for one thread timeline.

    Transport responsibilities handled here:
    - initial cursor resolution and cold-start behavior
    - SSE framing
    - request disconnect checks
    - event-bus subscription lifecycle
    - short debounce/coalescing after bus wakeups
    - idle heartbeats

    Semantic replay/reset logic is delegated to the app service. This iterator
    treats bus events only as wake-up hints, then re-queries the DB to compute
    the actual stream event to send.
    """

    queue: Queue[object] = Queue()

    def _on_runtime_event(_event) -> None:
        queue.put_nowait(object())

    subscription = bus.subscribe(_on_runtime_event, thread_id=thread_id)
    cursor = after_cursor

    try:
        initial_event = build_initial_thread_stream_event(
            db,
            thread_id=thread_id,
            after_cursor=cursor,
        )
        if initial_event is not None:
            cursor = initial_event.cursor
            yield _encode_sse(ThreadStreamEnvelopeResponse(**initial_event.model_dump()))

        while True:
            if await request.is_disconnected():
                break

            try:
                await asyncio.to_thread(queue.get, True, STREAM_HEARTBEAT_SECONDS)
            except Empty:
                heartbeat = build_thread_stream_heartbeat(thread_id=thread_id, cursor=cursor or 0)
                yield _encode_sse(ThreadStreamEnvelopeResponse(**heartbeat.model_dump()))
                continue

            await asyncio.sleep(STREAM_DEBOUNCE_SECONDS)
            while True:
                try:
                    queue.get_nowait()
                except Empty:
                    break

            incremental_event = build_incremental_thread_stream_event(
                db,
                thread_id=thread_id,
                after_cursor=cursor or 0,
            )
            if incremental_event is None:
                continue
            cursor = incremental_event.cursor
            yield _encode_sse(ThreadStreamEnvelopeResponse(**incremental_event.model_dump()))
    finally:
        bus.unsubscribe(subscription)


def thread_stream(
    request: Request,
    thread_id: str,
    after_cursor: int | None = Query(default=None, ge=0),
    db: SqliteDb = Depends(get_agent_runtime_db),
    bus: InMemoryRuntimeEventBus = Depends(get_embedded_agent_runtime_event_bus),
) -> StreamingResponse:
    """Open a cursor-replayable SSE stream for one assistant thread.

    High-level protocol:
    - Cold-start clients receive a full `snapshot`.
    - Reconnecting clients may send `after_cursor` or rely on `Last-Event-ID`.
    - The server replays from the DB when possible.
    - If replay continuity is not safe, the server emits `reset` with a full
      replacement payload.
    - During idle periods, the server emits `heartbeat`.
    - Bus wakeups with shell-only changes may emit `thread_updated`.

    The response body is `text/event-stream`. The JSON envelope inside each
    `data:` frame is documented in `thread_stream/schema.py`.
    """

    resolved_cursor = _cursor_from_request(request=request, after_cursor=after_cursor)
    detail = get_thread_detail(db, thread_id=thread_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    return StreamingResponse(
        _thread_stream_iterator(
            request=request,
            db=db,
            bus=bus,
            thread_id=thread_id,
            after_cursor=resolved_cursor,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
