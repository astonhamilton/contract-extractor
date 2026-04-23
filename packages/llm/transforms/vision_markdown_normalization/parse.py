from __future__ import annotations


def clean_vision_markdown_output(text: str) -> str:
    """Strip fenced wrappers and normalize trailing whitespace from markdown output."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped
