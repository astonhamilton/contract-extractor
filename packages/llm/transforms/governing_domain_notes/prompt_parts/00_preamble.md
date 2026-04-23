Task:
Extract `GoverningDomainNotes` from one document already classified as a contracting-stage operative artifact.
This is a structured contract-map task, not full scalar extraction and not generic summarization.
Use the document content exactly as provided. Do not invent missing facts. Prefer narrow, grounded notes over weak inference.
Return exactly one JSON object and no surrounding prose.

Core analyst instructions:
- Treat the output as a domain-organized set of answer notes.
- Each answer should be short but substantive, usually 2-6 sentences when the document supports that much detail.
- Do not reduce the answer to two words if the document clearly says more.
- Do not write fluffy executive-summary prose.
- The job is to answer the important governance questions and cite where the answer lives.
- If the operative agreement explicitly states title, parties, term, fee, or payment mechanics, capture those facts even when deeper detail lives in incorporated materials.
- If the file contains support material, read the governing artifact first and use supporting material only when it clearly matters to the operative answer.

Reading order:
1. Identify the operative artifact in the file.
2. Read title and opening recital language.
3. Read parties and signature blocks.
4. Read term clauses.
5. Read scope/services clauses.
6. Read compensation/pricing clauses.
7. Read termination, insurance, performance, and compliance sections.
8. Use incorporated schedules or exhibits only as needed.

