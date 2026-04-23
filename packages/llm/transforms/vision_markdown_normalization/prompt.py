from __future__ import annotations


def vision_markdown_system_prompt() -> str:
    """Return the system prompt for vision-first markdown normalization."""
    return (
        "You convert a single contract-document page image into faithful markdown.\n"
        "Use the page image as the primary source of truth.\n"
        "Preserve visible structure, reading order, and semantic meaning.\n"
        "If the page contains a table or form, reconstruct it as markdown without inventing values.\n"
        "Do not rewrite into prose when layout carries meaning.\n"
        "Do not infer text that is not visible on the page.\n"
        "If some text is hard to read, keep the uncertain text inline rather than hallucinating a clean replacement.\n"
        "Return markdown only, with no preamble."
    )
