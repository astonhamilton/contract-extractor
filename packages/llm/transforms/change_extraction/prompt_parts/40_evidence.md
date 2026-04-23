Evidence Domain:
- Question answered: which clauses/pages should later extraction or review focus on?
- key_clauses should contain 1-5 clause anchors with label, summary, and citations.
- quality.warnings should capture ambiguity, mixed bundle, OCR weakness, target uncertainty, or unclear incorporation.
- quality.extraction_confidence should reflect confidence in the note set as a whole.
- top-level citations should contain the strongest overall supporting snippets.

Decision steps:
1. Prefer linkage, main delta, resulting-state, and execution clauses.
2. Choose a small number of high-value anchors rather than many low-value snippets.
3. Use warnings when the note set is partial or uncertain.
4. When secondary packet paperwork appears alongside a simple renewal or amendment, prefer recording that as a warning or secondary context rather than treating it as a separate contractual dimension.

Guardrails:
- Do not dump repetitive or low-signal snippets.
- Do not use headers/footers or generic cover pages when better operative clauses are available.
- Citations are part of the answer, not optional decoration.
