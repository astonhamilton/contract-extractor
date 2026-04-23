"""Single-shot task-oriented LLM runtime helpers."""

from packages.llm.shared.task_runtime.capabilities import (
    effective_reasoning_effort,
    model_supports_reasoning_effort,
    model_supports_strict_structured_output,
)
from packages.llm.shared.task_runtime.content import (
    build_markdown_user_content,
    build_repair_user_content,
    image_path_to_data_url,
    read_optional_text,
)
from packages.llm.shared.task_runtime.debug import usage_summary_from_debug_dir
from packages.llm.shared.task_runtime.structured import (
    completion_json_schema,
    validate_strict_json_schema,
)
from packages.llm.shared.task_runtime.text import completion_text, stream_completion_text

__all__ = [
    "build_markdown_user_content",
    "build_repair_user_content",
    "completion_json_schema",
    "completion_text",
    "effective_reasoning_effort",
    "image_path_to_data_url",
    "model_supports_reasoning_effort",
    "model_supports_strict_structured_output",
    "read_optional_text",
    "stream_completion_text",
    "usage_summary_from_debug_dir",
    "validate_strict_json_schema",
]
