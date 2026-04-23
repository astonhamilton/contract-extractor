from __future__ import annotations

from typing import Any

from packages.app_services.chat_assistant.models import (
    ThreadItemRecordView,
    ThreadItemsPage,
    ThreadItemSummary,
    ThreadItemView,
)
from packages.app_services.chat_assistant.thread_detail import thread_detail_from_record
from packages.app_services.chat_assistant.turns import turn_detail_from_record
from packages.data_store.connect import SqliteDb
from packages.data_store.llm_agent_runtime.queries.items import list_items, list_items_page
from packages.data_store.llm_agent_runtime.queries.assistant_turns import get_turn
from packages.data_store.llm_agent_runtime.queries.threads import get_thread


def _humanize(value: str | None) -> str:
    if not value:
        return "Event"
    return value.replace("_", " ").replace("-", " ").strip().title()


def _truncate(value: str | None, limit: int = 240) -> str:
    if not value:
        return ""
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _web_search_detail(payload: dict[str, Any], arguments: dict[str, object]) -> str:
    action = payload.get("action")
    query = payload.get("query") or arguments.get("query")
    if isinstance(query, str) and query.strip():
        if isinstance(action, str) and action.strip():
            return f"{_humanize(action)}: {query.strip()}"
        return query.strip()
    if isinstance(action, str) and action.strip():
        return _humanize(action)
    return "Hosted tool activity"


def summary_for_item(record: ThreadItemRecordView) -> ThreadItemSummary:
    if record.item_type == "message":
        title = _humanize(record.role)
        return ThreadItemSummary(title=title, detail=_truncate(record.content_text))

    if record.item_type == "tool_call":
        return ThreadItemSummary(
            title=_humanize(record.name),
            detail=_truncate(
                record.arguments.get("query") if isinstance(record.arguments.get("query"), str) else "Calling tool"
            ),
        )

    if record.item_type == "tool_result":
        detail = ""
        result_text = record.result.get("text")
        if isinstance(result_text, str):
            detail = _truncate(result_text)
        elif record.result:
            detail = _truncate(str(record.result))
        return ThreadItemSummary(
            title=_humanize(record.name or "tool_result"),
            detail=detail or "Tool result",
        )

    if record.item_type == "hosted_tool_event":
        title = _humanize(record.name or record.provider_item_type)
        payload = record.provider_payload if isinstance(record.provider_payload, dict) else {}
        if record.name == "web_search_call" or record.provider_item_type == "web_search_call":
            return ThreadItemSummary(
                title=title,
                detail=_truncate(_web_search_detail(payload, record.arguments)),
            )
        return ThreadItemSummary(
            title=title,
            detail=_truncate(str(payload or record.metadata or "Hosted tool event")),
        )

    if record.item_type == "reasoning":
        detail = ""
        summary = record.metadata.get("summary")
        if isinstance(summary, str):
            detail = summary
        elif record.provider_payload:
            detail = str(record.provider_payload)
        return ThreadItemSummary(title="Reasoning", detail=_truncate(detail))

    return ThreadItemSummary(
        title=_humanize(record.item_type),
        detail=_truncate(record.content_text or str(record.metadata or record.provider_payload or "")),
    )


def record_view_from_item(item) -> ThreadItemRecordView:
    return ThreadItemRecordView(
        item_id=item.item_id,
        seq=item.seq,
        item_type=item.item_type,
        role=item.role,
        name=item.name,
        content_text=item.content_text,
        arguments=item.arguments,
        result=item.result,
        provider_item_id=item.provider_item_id,
        provider_item_type=item.provider_item_type,
        provider_payload=item.provider_payload,
        metadata=item.metadata,
        created_at=item.created_at.isoformat(),
    )


def get_thread_items(
    db: SqliteDb,
    *,
    thread_id: str,
    page: int = 1,
    page_size: int = 100,
    item_type: str | None = None,
) -> ThreadItemsPage | None:
    """Return display-shaped paginated items for one thread."""
    with db.connect() as connection:
        thread = get_thread(connection, thread_id)
        if thread is None:
            return None
        active_turn = None
        if thread.active_turn_id:
            turn = get_turn(connection, thread.active_turn_id)
            if turn is not None:
                active_turn = turn_detail_from_record(turn)
        last_turn = None
        if thread.last_turn_id:
            turn = get_turn(connection, thread.last_turn_id)
            if turn is not None:
                last_turn = turn_detail_from_record(turn)

        item_views: list[ThreadItemView] = []
        items, total = list_items_page(
            connection,
            thread_id=thread_id,
            page=page,
            page_size=page_size,
            item_type=item_type,
        )
        for item in items:
            record = record_view_from_item(item)
            item_views.append(
                ThreadItemView(
                    summary=summary_for_item(record),
                    record=record,
                )
            )
        return ThreadItemsPage(
            thread=thread_detail_from_record(thread),
            active_turn=active_turn,
            last_turn=last_turn,
            items=item_views,
            total=total,
            page=max(page, 1),
            page_size=max(1, min(page_size, 100)),
        )


def thread_item_view_from_item(item) -> ThreadItemView:
    """Return one display-shaped item view from a persisted runtime item."""

    record = record_view_from_item(item)
    return ThreadItemView(
        summary=summary_for_item(record),
        record=record,
    )
