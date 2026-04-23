from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from apps.api.routes.thread_stream.handler import _thread_stream_iterator
from packages.data_store.connect import sqlite_connection, sqlite_db
from packages.data_store.llm_agent_runtime.commands.items import append_items
from packages.data_store.llm_agent_runtime.commands.threads import create_thread
from packages.data_store.llm_agent_runtime.models import ItemRecord, ThreadRecord
from packages.data_store.migrations import apply_pending_migrations
from packages.llm.shared.agent_runtime.event_bus import InMemoryRuntimeEventBus
from packages.llm.shared.agent_runtime.events import RuntimeEvent, RuntimeEventType


def _seed_runtime_db(db_path: Path) -> None:
    with sqlite_connection(db_path) as connection:
        apply_pending_migrations(connection)
        create_thread(
            connection,
            ThreadRecord(
                thread_id="thread_test",
                thread_kind="conversation",
                agent_id="corpus_assistant",
                title="Test thread",
            ),
        )
        append_items(
            connection,
            [
                ItemRecord(
                    item_id="item_1",
                    thread_id="thread_test",
                    item_type="message",
                    role="user",
                    content_text="First message",
                ),
                ItemRecord(
                    item_id="item_2",
                    thread_id="thread_test",
                    item_type="message",
                    role="assistant",
                    content_text="Second message",
                ),
            ],
        )
        connection.commit()


class _FakeRequest:
    def __init__(self, headers: dict[str, str] | None = None) -> None:
        self.headers = headers or {}

    async def is_disconnected(self) -> bool:
        return False


def _parse_sse_frame(frame: str) -> dict[str, object]:
    event_name: str | None = None
    event_id: str | None = None
    payload = ""

    for line in frame.strip().splitlines():
        if line.startswith("event: "):
            event_name = line[len("event: ") :]
        elif line.startswith("id: "):
            event_id = line[len("id: ") :]
        elif line.startswith("data: "):
            payload += line[len("data: ") :]

    return {
        "event": event_name,
        "id": event_id,
        "data": json.loads(payload),
    }


class ThreadStreamRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "runtime.db"
        _seed_runtime_db(self.db_path)
        self.bus = InMemoryRuntimeEventBus()
        self.db = sqlite_db(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_iterator_returns_initial_snapshot_frame(self) -> None:
        async def run_test() -> dict[str, object]:
            iterator = _thread_stream_iterator(
                request=_FakeRequest(),
                db=self.db,
                bus=self.bus,
                thread_id="thread_test",
                after_cursor=None,
            )
            try:
                frame = await anext(iterator)
            finally:
                await iterator.aclose()
            return _parse_sse_frame(frame)

        event = asyncio.run(run_test())
        self.assertEqual(event["event"], "snapshot")
        self.assertEqual(event["id"], "2")
        self.assertEqual(event["data"]["cursor"], 2)
        self.assertEqual(len(event["data"]["payload"]["items"]), 2)

    def test_iterator_replays_from_cursor(self) -> None:
        async def run_test() -> dict[str, object]:
            iterator = _thread_stream_iterator(
                request=_FakeRequest(headers={"last-event-id": "1"}),
                db=self.db,
                bus=self.bus,
                thread_id="thread_test",
                after_cursor=1,
            )
            try:
                frame = await anext(iterator)
            finally:
                await iterator.aclose()
            return _parse_sse_frame(frame)

        event = asyncio.run(run_test())
        self.assertEqual(event["event"], "items_appended")
        self.assertEqual(event["id"], "2")
        self.assertEqual(len(event["data"]["payload"]["items"]), 1)
        self.assertEqual(event["data"]["payload"]["items"][0]["record"]["seq"], 2)

    def test_iterator_emits_incremental_append_after_bus_wakeup(self) -> None:
        async def run_test() -> tuple[dict[str, object], dict[str, object]]:
            iterator = _thread_stream_iterator(
                request=_FakeRequest(),
                db=self.db,
                bus=self.bus,
                thread_id="thread_test",
                after_cursor=None,
            )
            try:
                first_frame = await anext(iterator)

                with sqlite_connection(self.db_path) as connection:
                    append_items(
                        connection,
                        [
                            ItemRecord(
                                item_id="item_3",
                                thread_id="thread_test",
                                item_type="message",
                                role="assistant",
                                content_text="Third message",
                            )
                        ],
                    )
                    connection.commit()

                self.bus.emit(
                    RuntimeEvent(
                        event_id="evt_1",
                        event_type=RuntimeEventType.TURN_COMPLETED,
                        thread_id="thread_test",
                        payload={},
                    )
                )

                second_frame = await anext(iterator)
            finally:
                await iterator.aclose()
            return _parse_sse_frame(first_frame), _parse_sse_frame(second_frame)

        first_event, second_event = asyncio.run(run_test())
        self.assertEqual(first_event["event"], "snapshot")
        self.assertEqual(second_event["event"], "items_appended")
        self.assertEqual(second_event["id"], "3")
        self.assertEqual(len(second_event["data"]["payload"]["items"]), 1)
        self.assertEqual(second_event["data"]["payload"]["items"][0]["record"]["seq"], 3)


if __name__ == "__main__":
    unittest.main()
