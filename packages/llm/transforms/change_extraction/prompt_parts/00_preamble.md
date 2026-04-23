Task:
Extract lightweight, retrieval-oriented change domain notes for one change artifact.
This is not a full before/after normalization task.
The goal is to produce stable domain notes plus cited anchors that help later question-specific extraction.
Return exactly one JSON object and no surrounding prose.

Core rules:
- Read the document as a change to a prior artifact, not as a full governing contract.
- Prefer short, honest notes over brittle field-by-field guesses.
- Prefer null or [] over weak inference.
- Use the classified change kind only as context; do not force the document into details it does not support.
- Prioritize retrieval utility: what changed, what it appears to affect, what post-change state is explicit, and which clauses/pages matter.
- If the file is mixed, anchor the output to the operative change instrument and note ambiguity in warnings.
- Do not invent exact identifiers, dates, prior values, or resulting values when the document does not state them clearly.
