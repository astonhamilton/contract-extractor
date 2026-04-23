from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from packages.data_store.llm_agent_runtime.common import dumps_json, next_item_seq
from packages.data_store.llm_agent_runtime.models import ItemRecord


def append_items(connection: sqlite3.Connection, items: Sequence[ItemRecord]) -> list[ItemRecord]:
    """Append thread items and assign sequence numbers when missing."""
    if not items:
        return []
    next_seq = next_item_seq(connection, items[0].thread_id)
    persisted: list[ItemRecord] = []
    for item in items:
        seq = item.seq if item.seq is not None else next_seq
        next_seq = max(next_seq, seq + 1)
        persisted_item = item.model_copy(update={"seq": seq})
        connection.execute(
            """
            INSERT INTO asst_items (
                item_id, thread_id, turn_id, model_call_id, parent_item_id, seq, item_type,
                role, content_text, name, arguments_json, result_json, provider_item_id,
                provider_item_type, provider_payload_json, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                persisted_item.item_id,
                persisted_item.thread_id,
                persisted_item.turn_id,
                persisted_item.model_call_id,
                persisted_item.parent_item_id,
                persisted_item.seq,
                persisted_item.item_type,
                persisted_item.role,
                persisted_item.content_text,
                persisted_item.name,
                dumps_json(persisted_item.arguments),
                dumps_json(persisted_item.result),
                persisted_item.provider_item_id,
                persisted_item.provider_item_type,
                dumps_json(persisted_item.provider_payload),
                dumps_json(persisted_item.metadata),
                persisted_item.created_at.isoformat(),
            ),
        )
        persisted.append(persisted_item)
    return persisted
