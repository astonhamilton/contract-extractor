from __future__ import annotations

from packages.llm.agents.app.corpus_assistant.prompt import system_prompt
from packages.llm.agents.app.corpus_assistant.tool_registry import build_corpus_tool_registry
from packages.llm.shared.agent_runtime.hosted_tools import (
    openai_image_generation,
    openai_web_search_preview,
)
from packages.llm.shared.agent_runtime.models import AgentSpec


def build_corpus_assistant_agent_spec() -> AgentSpec:
    """Return the registered agent spec for the corpus assistant."""
    return AgentSpec(
        agent_id="corpus_assistant.v1",
        instructions=system_prompt(),
        default_provider="openai",
        default_model="openai/gpt-5.4-mini",
        local_tools=build_corpus_tool_registry().definitions(),
        hosted_tools=[
            openai_web_search_preview(search_context_size="medium"),
            openai_image_generation(size="1024x1024", quality="medium"),
        ],
    )
