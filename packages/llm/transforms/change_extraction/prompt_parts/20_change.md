Change Domain:
- Question answered: what are the main operative changes?
- change.answer should be a concise prose summary of the main delta.
- change.dimensions should be zero or more coarse routing tags from: term, pricing, scope, control, other.
- change.citations should point to the main operative delta clauses.

Dimension meanings:
- term: renewal, extension, shortening, or other direct change to the contract period itself.
- pricing: rates, fees, credits, caps, reimbursement amounts, unit prices, or other commercial amount mechanics.
- scope: services, products, deliverables, included/excluded work, or operative responsibilities being changed.
- control: reporting, invoicing, notice, approvals, documentation, compliance, audit, submission, or admin-process mechanics when those mechanics are themselves being amended.
- other: use sparingly, only for a real operative delta that does not fit the listed coarse buckets.

Dimension policy:
- These are coarse routing hints, not a complete semantic breakdown of the document.
- One dimension is often enough.
- If the prose note already captures nuance, do not force extra dimensions.

Decision steps:
1. Find the operative delta clause or clauses.
2. Summarize the actual change, not the whole contract or procurement background.
3. Include every explicit change theme that materially matters.
4. Add only the smallest useful set of coarse dimensions.
5. Tag only operative change themes; ancillary renewal instructions, vendor reminders, or packet requirements do not deserve dimensions unless the instrument itself amends a control/process term.
6. If a renewal or amendment packet includes follow-up asks like updated COIs, disclosure statements, insurance evidence, or contact confirmations, keep them as secondary prose context or warnings rather than dimensions unless the document explicitly says those process terms are being amended.
7. For a simple renewal letter that extends the term and continues the existing terms and conditions, default to `term` only.
8. Do not use `term` for pricing-update effective dates, contract-year references, anniversary periods, or priced service periods unless the document actually extends, shortens, or otherwise amends the contract period itself.

Guardrails:
- Do not restate the whole contract.
- Do not collapse a multi-part change into one oversimplified theme.
- Do not use operational scheduling or incidental logistics as the main change unless the document clearly makes that operative.
- Do not use `control` for routine follow-up requests like updated COIs, disclosure forms, insurance certificates, or contact reminders in renewal packets.
- Do not use `control` just because a document says "formal notice to renew" or contains renewal-notice wording; use it only when the notice/control mechanics themselves are changed.
- Do not use `control` just because the amendment assigns the agreement to a new party or incorporates an exhibit, attachment, or federal requirements addendum; those belong under scope, control, or prose context only if the operative control mechanics are actually amended.
- Do not use other as a catch-all when term, pricing, scope, or control already explain the change.
