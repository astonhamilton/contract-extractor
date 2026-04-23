# Question Type: Governing Document Identification Learnings

General learnings for this question type:

- Start with a small ranked candidate set rather than chasing the whole corpus.
- Usually the top three candidates are enough for first-pass analysis.
- The point of page-note and page retrieval is to identify the smallest set of pages likely to answer the user's question.
- `operative` documents are usually the strongest candidates when the question is about the base agreement or the document that governs the relationship.
- `delta` documents matter when the answer may depend on renewals, amendments, extensions, or later changes to that base agreement.
- `context` documents usually provide surrounding background and should not control the answer unless they clearly say that they do.
- Use `get_document_notes` early because it helps you quickly understand what role a document appears to play and whether it is worth deeper inspection.
- If page notes exist, use them before raw page retrieval.
- Page notes are a document map, not final evidence.
- Use `get_page` or `get_pages` to retrieve only the pages needed to answer the question.
- Full-document retrieval is a last resort when page notes do not exist or do not let you isolate a useful page subset.
- For governing-state questions, the correct answer may be one document or a governing document set.
- A common correct answer shape is:
  - the base agreement appears to govern the relationship
  - as later renewed, amended, or extended by specific change documents
- Do not collapse the base agreement and later change documents into one vague statement if the corpus supports a more precise answer.
