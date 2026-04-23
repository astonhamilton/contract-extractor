from __future__ import annotations


def retrieval_policy() -> str:
    """Return the high-level retrieval policy for the corpus assistant."""
    return (
        "Prefer document-map tools first, then page-note tools, then raw page fetches, "
        "and only pull full-document content when narrower retrieval is insufficient."
    )
