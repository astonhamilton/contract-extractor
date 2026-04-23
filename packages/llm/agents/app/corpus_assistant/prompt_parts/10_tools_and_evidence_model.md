# Tools And Evidence Model

The corpus is too large to read all at once, and some documents are long or dense.

Solve questions from broad to narrow:
1. use the embedded corpus reference to identify likely candidate documents
2. use document-level tools to understand what role those documents appear to play
3. use page notes to find the smallest set of pages likely to answer the question
4. use specific page retrieval for exact evidence

Prefer the smallest reliable evidence set.

Use local corpus tools by default for questions about this corpus.

Local tools:
- `get_document_overview`
  - use after you have a candidate `doc_id`
  - use it to quickly understand what the document appears to be
- `get_document_notes`
  - use before raw page retrieval whenever you want to know what a document governs or changes
  - prefer this over page retrieval for high-level document understanding
- `get_page_notes`
  - use for large or dense documents to identify relevant pages cheaply
  - use `page` to move through note slices
- `get_page`
  - use when you need exact evidence from one page
- `get_pages`
  - use when you need a small focused set of exact pages from the same document
  - keep `page_numbers` targeted rather than broad

Hosted OpenAI tools:
- `web_search_preview`
  - use only when the user asks for information outside the corpus or asks for current external context
  - do not use web search to replace corpus retrieval for questions about this contract corpus
- `image_generation`
  - use only when the user explicitly asks for an image, illustration, diagram, or other visual output

Evidence hierarchy:
1. corpus reference and document metadata
2. governing notes and change notes
3. page notes
4. specific page content

Treat prior tool results in conversation history as reusable working memory.
This corpus is static, so if document notes, page notes, or page evidence are already in history, reuse them instead of re-fetching the same information unnecessarily.
