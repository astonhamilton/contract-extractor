from __future__ import annotations


def system_prompt() -> str:
    """Return the system prompt for short thread-title generation."""
    return (
        "You write concise thread titles for user requests. "
        "Your job is to summarize the user's underlying request as a short title, not answer it. "
        "Return only the title text. "
        "Keep it specific, natural, and short, usually 3 to 8 words and under 60 characters. "
        "Prefer noun-phrase or imperative titles that would look good in a sidebar. "
        "Do not use quotes. "
        "Do not add labels, prefixes, markdown, explanations, or trailing punctuation unless truly needed."
    )


def build_title_request_prompt(user_text: str) -> str:
    """Wrap one user message as an explicit titling task for the agent."""
    cleaned = " ".join(user_text.replace("\n", " ").split()).strip()
    return (
        "Generate a short thread title for the following user message.\n"
        "Return only the title text.\n\n"
        f"User message:\n{cleaned}"
    )
