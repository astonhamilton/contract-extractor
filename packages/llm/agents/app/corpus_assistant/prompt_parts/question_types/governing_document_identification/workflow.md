# Question Type: Governing Document Identification Workflow

This workflow applies to questions like:
- What document currently governs this vendor relationship?
- Which agreement is in force?
- What document appears to control this relationship today?
- What is the base governing agreement for this vendor?
- Is this document the governing agreement or just a renewal, amendment, or support document?

Use this workflow:

1. Start with the embedded corpus reference.
   - identify a small candidate set, usually the top three likely documents
   - rank them using seller match, buyer match, subject match, lifecycle role, document-map type, and note availability
2. Use `get_document_overview` on the strongest candidates.
   - use it to quickly validate what each candidate appears to be
3. Use `get_document_notes` on the strongest one or two candidates.
   - use it to understand whether the document appears to be a base governing document, a later change document, or supporting material
4. If a candidate has page notes, use `get_page_notes`.
   - use page notes to identify the smallest set of pages likely to answer the user's question
5. Use `get_page` or `get_pages` for exact evidence.
   - use `get_page` when one page is likely enough
   - use `get_pages` when a small set of pages from the same document is likely enough
6. If page notes do not exist or do not let you identify a useful page subset, escalate to full-document retrieval if that capability is available.
7. Answer by separating:
   - the likely base governing document
   - later change or renewal documents if they matter
   - the resulting current governing state when the corpus supports it

The goal of this workflow is to answer:
- what the base governing document is
- whether later change documents affect the answer
- whether the current governing relationship is one document or a document set

Do not force a single-document answer if the evidence instead supports:
- a base agreement
- plus later renewals, amendments, or extensions that remain part of the current governing state
