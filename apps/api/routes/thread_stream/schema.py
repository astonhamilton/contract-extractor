"""Transport schema for `GET /threads/{thread_id}/stream`.

This route uses Server-Sent Events (SSE). The HTTP response is an open
`text/event-stream` connection rather than a normal JSON document.

Protocol contract:
- The stream emits named SSE events:
  - `snapshot`
  - `items_appended`
  - `thread_updated`
  - `heartbeat`
  - `reset`
- Each SSE `data:` line contains one JSON envelope described by
  `ThreadStreamEnvelopeResponse`.
- The SSE `id:` field mirrors the envelope cursor so browsers can reconnect with
  `Last-Event-ID`.

Cursor semantics:
- Cursor is the highest thread item sequence the client has fully applied.
- Cold start:
  - client connects without a cursor
  - server emits `snapshot`
- Resume:
  - client reconnects with `after_cursor` or `Last-Event-ID`
  - server replays missing items if possible
  - server emits `reset` if replay is not safe

Client rules:
- `snapshot`: replace local thread state with the payload
- `items_appended`: append payload items to local thread state
- `thread_updated`: replace only local thread shell metadata
- `heartbeat`: no state change
- `reset`: replace local thread state with the payload

Transport vs service boundary:
- This module documents the transport envelope used on the wire.
- The app service owns the semantic replay/snapshot logic.
- The route handler owns SSE framing, headers, keepalive timing, and bus
  subscription lifecycle.
"""

from __future__ import annotations

from typing import Literal

from packages.schemas.common import BaseSchema


class ThreadStreamEnvelopeResponse(BaseSchema):
    """JSON body carried inside each SSE `data:` frame.

    Fields:
    - `protocol_version`
      - protocol revision for compatible clients
    - `type`
      - one of `snapshot`, `items_appended`, `thread_updated`, `heartbeat`, `reset`
    - `thread_id`
      - thread this event applies to
    - `cursor`
      - highest fully-applied item sequence after applying this event
    - `sent_at`
      - server timestamp
    - `payload`
      - event-specific structured object
    """

    protocol_version: int
    type: Literal["snapshot", "items_appended", "thread_updated", "heartbeat", "reset"]
    thread_id: str
    cursor: int
    sent_at: str
    payload: dict[str, object]
