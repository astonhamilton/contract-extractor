from __future__ import annotations

import json
from pathlib import Path


def usage_summary_from_debug_dir(debug_dir: Path, *, max_tokens: int) -> dict[str, object]:
    """Summarize attempt usage and detect budget-exhaustion heuristics."""
    attempts: list[dict[str, object]] = []
    budget_exhausted = False

    for response_path in sorted(debug_dir.rglob("attempt_*_response.json")):
        response_payload = json.loads(response_path.read_text(encoding="utf-8"))
        response = response_payload.get("response")
        if not isinstance(response, dict):
            continue
        usage = response.get("usage")
        if not isinstance(usage, dict):
            continue
        choice_list = response.get("choices") or []
        content = None
        if isinstance(choice_list, list) and choice_list:
            first_choice = choice_list[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
        headers = response_payload.get("headers")
        if not isinstance(headers, dict):
            headers = {}
        completion_details = usage.get("completion_tokens_details")
        if not isinstance(completion_details, dict):
            completion_details = {}
        reasoning_tokens = completion_details.get("reasoning_tokens")
        completion_tokens = usage.get("completion_tokens")
        prompt_tokens = usage.get("prompt_tokens")
        total_tokens = usage.get("total_tokens")
        content_str = content if isinstance(content, str) else ""
        attempts.append(
            {
                "attempt": str(response_path.relative_to(debug_dir).with_suffix("")),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "reasoning_tokens": reasoning_tokens,
                "total_tokens": total_tokens,
                "content_length": len(content_str),
                "rate_limit_remaining_tokens": headers.get("x-ratelimit-remaining-tokens"),
                "rate_limit_reset_tokens": headers.get("x-ratelimit-reset-tokens"),
                "request_id": headers.get("x-request-id"),
            }
        )
        if (
            isinstance(completion_tokens, int)
            and isinstance(reasoning_tokens, int)
            and completion_tokens >= max_tokens
            and reasoning_tokens >= max_tokens
            and not content_str
        ):
            budget_exhausted = True

    totals = {
        "prompt_tokens": sum(item["prompt_tokens"] for item in attempts if isinstance(item.get("prompt_tokens"), int)),
        "completion_tokens": sum(item["completion_tokens"] for item in attempts if isinstance(item.get("completion_tokens"), int)),
        "reasoning_tokens": sum(item["reasoning_tokens"] for item in attempts if isinstance(item.get("reasoning_tokens"), int)),
        "total_tokens": sum(item["total_tokens"] for item in attempts if isinstance(item.get("total_tokens"), int)),
    }

    return {
        "attempts": attempts,
        "totals": totals,
        "heuristics": {
            "likely_output_budget_exhausted_by_reasoning": budget_exhausted,
        },
    }
