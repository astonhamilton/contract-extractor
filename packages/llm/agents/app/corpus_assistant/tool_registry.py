from __future__ import annotations

from packages.llm.shared.agent_runtime.tools import ToolRegistry
from packages.llm.tools.documents import register_document_tools


def build_corpus_tool_registry() -> ToolRegistry:
    """Return the corpus assistant's shared document-navigation tools."""
    registry = ToolRegistry()
    register_document_tools(registry)
    return registry
