from __future__ import annotations

from packages.llm.shared.agent_runtime.models import AgentSpec
from packages.llm.agents.app.thread_titling.prompt import system_prompt


def build_thread_titling_agent_spec() -> AgentSpec:
    """Return the thread-titling agent spec."""
    return AgentSpec(
        agent_id="thread_titling.v1",
        instructions=system_prompt(),
        default_provider="openai",
        default_model="openai/gpt-5.4-nano",
        local_tools=[],
        hosted_tools=[],
        metadata={"purpose": "thread_title_generation"},
    )
