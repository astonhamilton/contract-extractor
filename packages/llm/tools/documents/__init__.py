from __future__ import annotations

from packages.llm.shared.agent_runtime.tools import ToolRegistry
from packages.llm.tools.documents.get_document_notes import register_get_document_notes_tool
from packages.llm.tools.documents.get_document_overview import register_get_document_overview_tool
from packages.llm.tools.documents.get_page import register_get_page_tool
from packages.llm.tools.documents.get_page_notes import register_get_page_notes_tool
from packages.llm.tools.documents.get_pages import register_get_pages_tool


def register_document_tools(registry: ToolRegistry) -> ToolRegistry:
    """Register the shared document-navigation tools into one registry."""
    register_get_document_overview_tool(registry)
    register_get_document_notes_tool(registry)
    register_get_page_notes_tool(registry)
    register_get_page_tool(registry)
    register_get_pages_tool(registry)
    return registry
