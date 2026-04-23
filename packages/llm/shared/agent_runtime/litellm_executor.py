from __future__ import annotations

from litellm import completion
from litellm.responses.main import responses

from packages.llm.shared.agent_runtime.history import (
    provider_messages_from_items,
    response_output_items_from_responses_api,
    responses_input_from_items,
    tool_call_items_from_response,
)
from packages.llm.shared.agent_runtime.models import (
    AgentItem,
    HostedToolDefinition,
    ModelInvocationRequest,
    ModelInvocationResult,
)
from packages.llm.shared.agent_runtime.executor import AgentExecutor
from packages.llm.shared.strict_schema import enforce_openai_strict_required
from packages.llm.shared.task_runtime.capabilities import effective_reasoning_effort


def _local_tool_payload(
    *,
    tool_name: str,
    description: str,
    input_json_schema: dict[str, object],
) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": description,
            "parameters": input_json_schema or {"type": "object", "properties": {}, "required": []},
        }
    }


def _local_responses_tool_payload(
    *,
    tool_name: str,
    description: str,
    input_json_schema: dict[str, object],
) -> dict[str, object]:
    return {
        "type": "function",
        "name": tool_name,
        "description": description or None,
        "parameters": enforce_openai_strict_required(
            input_json_schema or {"type": "object", "properties": {}, "required": []}
        ),
        "strict": True,
    }


def _hosted_tool_payload(tool: HostedToolDefinition) -> dict[str, object]:
    payload = dict(tool.config)
    payload["type"] = tool.name
    return payload


def _provider_tools_for_chat(request: ModelInvocationRequest) -> list[dict[str, object]]:
    tools: list[dict[str, object]] = [
        _local_tool_payload(
            tool_name=tool.name,
            description=tool.description,
            input_json_schema=tool.input_json_schema,
        )
        for tool in request.local_tools
    ]
    tools.extend(
        _hosted_tool_payload(tool)
        for tool in request.hosted_tools
        if tool.enabled and (tool.provider is None or tool.provider == request.provider)
    )
    return tools


def _provider_tools_for_responses(request: ModelInvocationRequest) -> list[dict[str, object]]:
    tools: list[dict[str, object]] = [
        _local_responses_tool_payload(
            tool_name=tool.name,
            description=tool.description,
            input_json_schema=tool.input_json_schema,
        )
        for tool in request.local_tools
    ]
    tools.extend(
        _hosted_tool_payload(tool)
        for tool in request.hosted_tools
        if tool.enabled and (tool.provider is None or tool.provider == request.provider)
    )
    return tools


def _tool_choice(tools: list[dict[str, object]]) -> str | None:
    if not tools:
        return None
    return "auto"


def _supports_openai_responses_hosted_tools(request: ModelInvocationRequest) -> bool:
    if request.provider != "openai":
        return False
    return any(tool.enabled for tool in request.hosted_tools)


def _provider_request_options(request: ModelInvocationRequest) -> dict[str, object]:
    extras = request.provider_extras.get("request_options")
    if not isinstance(extras, dict):
        return {}
    reserved = {
        "model",
        "messages",
        "instructions",
        "input",
        "tools",
        "tool_choice",
        "reasoning",
        "reasoning_effort",
    }
    return {str(key): value for key, value in extras.items() if str(key) not in reserved}


class LiteLLMAgentExecutor(AgentExecutor):
    """LiteLLM-backed executor using chat-completion style tool calling."""

    def invoke(self, request: ModelInvocationRequest) -> ModelInvocationResult:
        if _supports_openai_responses_hosted_tools(request):
            return self._invoke_openai_responses(request)
        return self._invoke_chat_completion(request)

    def _invoke_chat_completion(self, request: ModelInvocationRequest) -> ModelInvocationResult:
        messages = provider_messages_from_items(
            items=request.items,
            system_prompt=request.instructions,
        )
        tools = _provider_tools_for_chat(request)
        reasoning_effort = effective_reasoning_effort(request.model, request.reasoning_effort)
        response = completion(
            model=request.model,
            messages=messages,
            tools=tools or None,
            tool_choice=_tool_choice(tools),
            reasoning_effort=reasoning_effort,
            **_provider_request_options(request),
        )

        response_payload = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        usage = response_payload.get("usage") if isinstance(response_payload, dict) else {}
        choices = response_payload.get("choices") if isinstance(response_payload, dict) else []
        first_choice = choices[0] if isinstance(choices, list) and choices else {}
        message = first_choice.get("message") if isinstance(first_choice, dict) else {}
        finish_reason = first_choice.get("finish_reason") if isinstance(first_choice, dict) else None
        content_text = message.get("content") if isinstance(message, dict) else None
        tool_calls = message.get("tool_calls") if isinstance(message, dict) else None

        output_items: list[AgentItem] = []
        if isinstance(content_text, str) and content_text.strip():
            output_items.append(
                AgentItem(
                    thread_id=request.thread_id,
                    turn_id=request.turn_id,
                    model_call_id=request.model_call_id,
                    item_type="message",
                    role="assistant",
                    content_text=content_text.strip(),
                    provider_payload={"message": message},
                )
            )

        tool_request_items, tool_requests = tool_call_items_from_response(
            thread_id=request.thread_id,
            turn_id=request.turn_id,
            model_call_id=request.model_call_id,
            tool_calls=tool_calls,
        )
        output_items.extend(tool_request_items)

        return ModelInvocationResult(
            output_items=output_items,
            tool_requests=tool_requests,
            usage=usage if isinstance(usage, dict) else {},
            raw_response=response_payload if isinstance(response_payload, dict) else {},
            provider_response_id=response_payload.get("id") if isinstance(response_payload, dict) else None,
            provider_request_id=None,
            provider_conversation_id=None,
            continuation={},
            finish_reason=finish_reason,
        )

    def _invoke_openai_responses(self, request: ModelInvocationRequest) -> ModelInvocationResult:
        tools = _provider_tools_for_responses(request)
        reasoning_effort = effective_reasoning_effort(request.model, request.reasoning_effort)
        raw_response = responses(
            model=request.model,
            instructions=request.instructions or None,
            input=responses_input_from_items(items=request.items),
            tools=tools or None,
            tool_choice=_tool_choice(tools),
            reasoning={"effort": reasoning_effort} if reasoning_effort else None,
            include=[
                "web_search_call.results",
                "web_search_call.action.sources",
                "file_search_call.results",
                "reasoning.encrypted_content",
            ],
            **_provider_request_options(request),
        )
        response_payload = raw_response.model_dump() if hasattr(raw_response, "model_dump") else dict(raw_response)
        output_items, tool_requests = response_output_items_from_responses_api(
            thread_id=request.thread_id,
            turn_id=request.turn_id,
            model_call_id=request.model_call_id,
            output=response_payload.get("output"),
        )
        usage = response_payload.get("usage") if isinstance(response_payload, dict) else {}
        return ModelInvocationResult(
            output_items=output_items,
            tool_requests=tool_requests,
            usage=usage if isinstance(usage, dict) else {},
            raw_response=response_payload if isinstance(response_payload, dict) else {},
            provider_response_id=response_payload.get("id") if isinstance(response_payload, dict) else None,
            provider_request_id=None,
            provider_conversation_id=(
                (response_payload.get("conversation") or {}).get("id")
                if isinstance(response_payload, dict) and isinstance(response_payload.get("conversation"), dict)
                else None
            ),
            continuation={},
            finish_reason=response_payload.get("status") if isinstance(response_payload, dict) else None,
        )


__all__ = ["LiteLLMAgentExecutor"]
