from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from packages.app_services.chat_assistant.stream import (
    build_incremental_thread_stream_event,
    build_initial_thread_stream_event,
    build_thread_stream_heartbeat,
)
from packages.data_store.connect import sqlite_connection
from packages.data_store.llm_agent_runtime.commands.items import append_items
from packages.data_store.llm_agent_runtime.commands.threads import create_thread
from packages.data_store.llm_agent_runtime.models import ItemRecord, ThreadRecord
from packages.data_store.migrations import apply_pending_migrations


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


class ThreadStreamServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "runtime.db"
        _seed_runtime_db(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_initial_stream_without_cursor_returns_snapshot(self) -> None:
        with sqlite_connection(self.db_path) as connection:
            event = build_initial_thread_stream_event(
                connection,
                thread_id="thread_test",
                after_cursor=None,
            )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.type, "snapshot")
        self.assertEqual(event.cursor, 2)
        self.assertEqual(event.payload["thread"]["thread_id"], "thread_test")
        self.assertEqual(len(event.payload["items"]), 2)

    def test_valid_cursor_replays_only_new_items(self) -> None:
        with sqlite_connection(self.db_path) as connection:
            event = build_initial_thread_stream_event(
                connection,
                thread_id="thread_test",
                after_cursor=1,
            )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.type, "items_appended")
        self.assertEqual(event.cursor, 2)
        self.assertEqual(len(event.payload["items"]), 1)
        self.assertEqual(event.payload["items"][0]["record"]["seq"], 2)

    def test_current_cursor_has_no_incremental_event(self) -> None:
        with sqlite_connection(self.db_path) as connection:
            event = build_incremental_thread_stream_event(
                connection,
                thread_id="thread_test",
                after_cursor=2,
            )

        self.assertIsNone(event)

    def test_ahead_cursor_forces_reset_snapshot(self) -> None:
        with sqlite_connection(self.db_path) as connection:
            event = build_initial_thread_stream_event(
                connection,
                thread_id="thread_test",
                after_cursor=99,
            )

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.type, "reset")
        self.assertEqual(event.cursor, 2)
        self.assertEqual(event.payload["reason"], "cursor_out_of_range")
        self.assertEqual(len(event.payload["items"]), 2)

    def test_heartbeat_reflects_cursor(self) -> None:
        event = build_thread_stream_heartbeat(thread_id="thread_test", cursor=2)

        self.assertEqual(event.type, "heartbeat")
        self.assertEqual(event.thread_id, "thread_test")
        self.assertEqual(event.cursor, 2)
        self.assertEqual(event.payload["status"], "ok")


if __name__ == "__main__":
    unittest.main()
