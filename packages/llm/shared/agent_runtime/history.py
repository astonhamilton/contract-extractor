from __future__ import annotations

import json
from collections.abc import Sequence

from packages.llm.shared.agent_runtime.models import AgentItem, ToolCallRequest


def visible_thread_items(items: Sequence[AgentItem]) -> list[AgentItem]:
    """Return persisted thread items that should participate in provider replay."""
    return [item for item in items if item.item_type != "reasoning"]


def provider_messages_from_items(
    *,
    items: Sequence[AgentItem],
    system_prompt: str,
) -> list[dict[str, object]]:
    """Convert canonical thread items into chat-completions style provider messages."""
    messages: list[dict[str, object]] = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})

    tool_call_groups: dict[str, list[AgentItem]] = {}
    for item in visible_thread_items(items):
        if item.item_type == "tool_call" and item.model_call_id:
            tool_call_groups.setdefault(item.model_call_id, []).append(item)

    emitted_tool_groups: set[str] = set()
    for item in items:
        if item.item_type == "message" and item.role in {"user", "assistant", "system", "developer"}:
            messages.append(
                {
                    "role": "assistant" if item.role == "developer" else item.role,
                    "content": item.content_text or "",
                }
            )
            if item.model_call_id and item.model_call_id in tool_call_groups and item.model_call_id not in emitted_tool_groups:
                messages[-1]["tool_calls"] = [
                    {
                        "id": tool_item.item_id,
                        "type": "function",
                        "function": {
                            "name": tool_item.name,
                            "arguments": json.dumps(tool_item.arguments),
                        },
                    }
                    for tool_item in tool_call_groups[item.model_call_id]
                ]
                emitted_tool_groups.add(item.model_call_id)
            continue
        if item.item_type == "tool_call":
            if item.model_call_id and item.model_call_id in emitted_tool_groups:
                continue
            call_group = tool_call_groups.get(item.model_call_id or "", [item])
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": tool_item.item_id,
                            "type": "function",
                            "function": {
                                "name": tool_item.name,
                                "arguments": json.dumps(tool_item.arguments),
                            },
                        }
                        for tool_item in call_group
                    ],
                }
            )
            if item.model_call_id:
                emitted_tool_groups.add(item.model_call_id)
            continue
        if item.item_type == "tool_result":
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item.metadata.get("tool_call_id") or item.parent_item_id or item.item_id,
                    "content": json.dumps(item.result or {"text": item.content_text or ""}),
                }
            )
    return messages


def responses_input_from_items(
    *,
    items: Sequence[AgentItem],
) -> list[dict[str, object]]:
    """Convert canonical thread items into OpenAI Responses-style input items."""
    tool_call_ids_by_item_id: dict[str, tuple[str, str]] = {}
    for item in items:
        if item.item_type != "tool_call":
            continue
        provider_payload = item.provider_payload if isinstance(item.provider_payload, dict) else {}
        function_item_id = str(provider_payload.get("id") or item.provider_item_id or item.item_id)
        provider_call_id = str(provider_payload.get("call_id") or item.provider_item_id or item.item_id)
        tool_call_ids_by_item_id[item.item_id] = (function_item_id, provider_call_id)

    input_items: list[dict[str, object]] = []
    for item in items:
        if item.item_type == "message" and item.role in {"user", "assistant", "system", "developer"}:
            input_items.append(
                {
                    "type": "message",
                    "role": item.role,
                    "content": item.content_text or "",
                }
            )
            continue
        if item.item_type == "tool_call":
            function_item_id, provider_call_id = tool_call_ids_by_item_id.get(
                item.item_id,
                (item.provider_item_id or item.item_id, item.provider_item_id or item.item_id),
            )
            input_items.append(
                {
                    "type": "function_call",
                    "id": function_item_id,
                    "call_id": provider_call_id,
                    "name": item.name or "",
                    "arguments": json.dumps(item.arguments or {}),
                }
            )
            continue
        if item.item_type == "tool_result":
            parent_function_ids = (
                tool_call_ids_by_item_id.get(item.parent_item_id or "")
                if item.parent_item_id
                else None
            )
            provider_call_id = (
                item.metadata.get("tool_call_provider_id")
                or item.metadata.get("tool_call_call_id")
                or (parent_function_ids[1] if parent_function_ids else None)
                or item.metadata.get("tool_call_id")
                or item.parent_item_id
                or item.item_id
            )
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": provider_call_id,
                    "output": json.dumps(item.result or {"text": item.content_text or ""}),
                }
            )
            continue
        if item.item_type == "reasoning" and isinstance(item.provider_payload, dict):
            input_items.append(_responses_reasoning_input(item.provider_payload))
            continue
        if item.item_type == "hosted_tool_event" and isinstance(item.provider_payload, dict):
            input_items.append(_responses_hosted_tool_input(item.provider_payload))
    return input_items


def _responses_reasoning_input(payload: dict[str, object]) -> dict[str, object]:
    """Return the OpenAI Responses replay shape for one reasoning item."""
    replay: dict[str, object] = {
        "id": payload.get("id"),
        "type": "reasoning",
        "summary": payload.get("summary") or [],
    }
    if "content" in payload:
        replay["content"] = payload.get("content")
    if "encrypted_content" in payload:
        replay["encrypted_content"] = payload.get("encrypted_content")
    if "status" in payload:
        replay["status"] = payload.get("status")
    return replay


def _responses_hosted_tool_input(payload: dict[str, object]) -> dict[str, object]:
    """Return the OpenAI Responses replay shape for one hosted tool item."""
    item_type = payload.get("type")
    replay: dict[str, object] = {
        "id": payload.get("id"),
        "type": item_type,
    }
    if "status" in payload:
        replay["status"] = payload.get("status")

    if item_type == "image_generation_call":
        if "result" in payload:
            replay["result"] = payload.get("result")
        return replay

    if item_type in {"web_search_call", "file_search_call", "computer_call", "computer_call_output"}:
        return replay

    return {
        key: value
        for key, value in payload.items()
        if key in {"id", "type", "status", "result"}
    }


def tool_call_items_from_response(
    *,
    thread_id: str,
    turn_id: str,
    model_call_id: str,
    tool_calls: object,
) -> tuple[list[AgentItem], list[ToolCallRequest]]:
    """Convert provider tool-call blocks into canonical tool-call items and requests."""
    if not isinstance(tool_calls, list):
        return [], []
    items: list[AgentItem] = []
    requests: list[ToolCallRequest] = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        function = tool_call.get("function")
        if not isinstance(function, dict):
            continue
        tool_name = function.get("name")
        if not isinstance(tool_name, str) or not tool_name:
            continue
        arguments_raw = function.get("arguments")
        arguments: dict[str, object] = {}
        if isinstance(arguments_raw, str) and arguments_raw.strip():
            try:
                parsed = json.loads(arguments_raw)
                if isinstance(parsed, dict):
                    arguments = parsed
            except json.JSONDecodeError:
                arguments = {"raw_arguments": arguments_raw}
        item = AgentItem(
            thread_id=thread_id,
            turn_id=turn_id,
            model_call_id=model_call_id,
            item_type="tool_call",
            role="assistant",
            name=tool_name,
            arguments=arguments,
            provider_item_id=str(tool_call.get("id")) if tool_call.get("id") else None,
            provider_item_type=str(tool_call.get("type")) if tool_call.get("type") else "function",
            provider_payload=tool_call,
        )
        items.append(item)
        requests.append(
            ToolCallRequest(
                tool_name=tool_name,
                arguments=arguments,
                provider_item_id=item.provider_item_id,
                item_id=item.item_id,
            )
        )
    return items, requests


def response_output_items_from_responses_api(
    *,
    thread_id: str,
    turn_id: str,
    model_call_id: str,
    output: object,
) -> tuple[list[AgentItem], list[ToolCallRequest]]:
    """Convert Responses API output items into canonical runtime items."""
    if not isinstance(output, list):
        return [], []

    items: list[AgentItem] = []
    tool_requests: list[ToolCallRequest] = []
    for response_item in output:
        if not isinstance(response_item, dict):
            continue
        item_type = response_item.get("type")
        if item_type == "message":
            content_parts = response_item.get("content")
            texts: list[str] = []
            if isinstance(content_parts, list):
                for part in content_parts:
                    if not isinstance(part, dict):
                        continue
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
            items.append(
                AgentItem(
                    thread_id=thread_id,
                    turn_id=turn_id,
                    model_call_id=model_call_id,
                    item_type="message",
                    role=str(response_item.get("role") or "assistant"),
                    content_text="\n\n".join(texts) if texts else None,
                    provider_item_id=str(response_item.get("id")) if response_item.get("id") else None,
                    provider_item_type=str(item_type),
                    provider_payload=response_item,
                )
            )
            continue
        if item_type == "function_call":
            tool_name = response_item.get("name")
            if not isinstance(tool_name, str) or not tool_name:
                continue
            arguments_raw = response_item.get("arguments")
            arguments: dict[str, object] = {}
            if isinstance(arguments_raw, str) and arguments_raw.strip():
                try:
                    parsed = json.loads(arguments_raw)
                    if isinstance(parsed, dict):
                        arguments = parsed
                except json.JSONDecodeError:
                    arguments = {"raw_arguments": arguments_raw}
            item = AgentItem(
                thread_id=thread_id,
                turn_id=turn_id,
                model_call_id=model_call_id,
                item_type="tool_call",
                role="assistant",
                name=tool_name,
                arguments=arguments,
                provider_item_id=str(response_item.get("call_id") or response_item.get("id") or ""),
                provider_item_type=str(item_type),
                provider_payload=response_item,
            )
            items.append(item)
            tool_requests.append(
                ToolCallRequest(
                    tool_name=tool_name,
                    arguments=arguments,
                    provider_item_id=item.provider_item_id,
                    item_id=item.item_id,
                )
            )
            continue
        canonical_item_type = "reasoning" if item_type == "reasoning" else "hosted_tool_event"
        items.append(
            AgentItem(
                thread_id=thread_id,
                turn_id=turn_id,
                model_call_id=model_call_id,
                item_type=canonical_item_type,
                role="assistant",
                name=str(item_type) if isinstance(item_type, str) else None,
                provider_item_id=str(response_item.get("id")) if response_item.get("id") else None,
                provider_item_type=str(item_type) if isinstance(item_type, str) else None,
                provider_payload=response_item,
                metadata={
                    "status": response_item.get("status"),
                },
            )
        )
    return items, tool_requests
