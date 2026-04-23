from __future__ import annotations


def markdown_system_prompt() -> str:
    """Return the system prompt for markdown normalization."""
    return (
        "You convert contract-document pages into faithful markdown.\n"
        "Preserve structure and semantic meaning.\n"
        "If the page contains a table, reconstruct it as markdown.\n"
        "Do not hallucinate missing cells or values.\n"
        "If text is unclear, keep the uncertain text but do not invent replacements.\n"
        "Prefer preserving row/column alignment over prose rewriting.\n"
        "Return markdown only, with no preamble."
    )
