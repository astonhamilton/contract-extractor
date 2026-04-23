from __future__ import annotations

from packages.schemas import ChangeKind, DocumentRole, ProcurementStage


def _enum_values(enum_type) -> str:
    """Return a comma-separated list of enum values for prompt inclusion."""
    return ", ".join(member.value for member in enum_type)


PRIMARY_ARTIFACT_LEARNINGS = (
    {
        "pattern": "A renewal letter or contract modification includes an attached vendor disclosure form.",
        "tempting_wrong_answer": "Treat the disclosure attachment as equally important and classify the file as compliance/context.",
        "why_tempting": "The disclosure pages can be visually obvious and contain repeated procurement labels.",
        "why_wrong": "The primary artifact is still the renewal or modification instrument; the disclosure form is secondary support material.",
        "general_rule": "Pick the dominant artifact the file is mainly about. Secondary attachments go in warnings, not in the core labels.",
    },
    {
        "pattern": "A standalone vendor disclosure statement contains fields labeled contract, bid, SOI, or renewal.",
        "tempting_wrong_answer": "Treat the form itself as a contract change or contracting artifact.",
        "why_tempting": "The labels reference other procurement artifacts and can look contract-like in isolation.",
        "why_wrong": "The form is still describing compliance context about another artifact rather than serving as that artifact.",
        "general_rule": "Contract-related labels inside a compliance form do not change the form's primary identity.",
    },
    {
        "pattern": "A signed SOW, task order, or project agreement says it is governed by a master agreement.",
        "tempting_wrong_answer": "Treat it as only contextual because another agreement sits above it.",
        "why_tempting": "The document is subordinate in hierarchy.",
        "why_wrong": "It can still be the primary operative artifact for the specific project work in the file.",
        "general_rule": "Primary artifact means the operative document in this file, not necessarily the highest-level legal umbrella.",
    },
)


PROCUREMENT_STAGE_LEARNINGS = (
    {
        "pattern": "An award letter names a vendor, contract number, and term details.",
        "tempting_wrong_answer": "procurement_stage=contracting",
        "why_tempting": "It talks about a contract relationship and may mention dates or pricing.",
        "why_wrong": "The document is still about the award event, not the executed contract artifact itself.",
        "general_rule": "Award and intent letters usually stay in award unless the file itself contains the operative executed contract.",
    },
    {
        "pattern": "A vendor disclosure or ethics form mentions a renewal period or contract number.",
        "tempting_wrong_answer": "procurement_stage=active_change or contracting",
        "why_tempting": "The form references another contract-stage artifact.",
        "why_wrong": "The document's own stage is still compliance.",
        "general_rule": "Stage follows the primary artifact, not the artifacts referenced inside it.",
    },
    {
        "pattern": "A signed agreement, SOW, or work order appears inside a mixed PDF with support material.",
        "tempting_wrong_answer": "procurement_stage=compliance or unclear because the file is mixed.",
        "why_tempting": "Support pages dilute the signal if the file is treated as an average of all pages.",
        "why_wrong": "If the dominant artifact is a signed operative contract instrument, the file is about contracting.",
        "general_rule": "Do not average across artifacts; classify the file by the stage of its primary artifact.",
    },
    {
        "pattern": "A modification, amendment, renewal, or extension includes substantive contract language.",
        "tempting_wrong_answer": "procurement_stage=contracting",
        "why_tempting": "The clauses can look like a full contract restatement.",
        "why_wrong": "The file is still about changing an existing procurement relationship.",
        "general_rule": "Changes belong in active_change even when they restate contract language.",
    },
)


DOCUMENT_ROLE_LEARNINGS = (
    {
        "pattern": "A signed SOW or executed agreement under a master contract contains scope, term, pricing, and signature blocks.",
        "tempting_wrong_answer": "primary_document_role=context",
        "why_tempting": "It is subordinate to another agreement and may be bundled with support material.",
        "why_wrong": "It carries operative procurement substance for the work described in the file.",
        "general_rule": "Signed project-level instruments are usually operative when they set the actual work terms.",
    },
    {
        "pattern": "A renewal letter, modification, amendment, or repricing instrument changes an existing relationship.",
        "tempting_wrong_answer": "primary_document_role=operative",
        "why_tempting": "The document can include binding signatures and contract clauses.",
        "why_wrong": "Its primary role is still to modify an existing procurement artifact rather than establish the base terms from scratch.",
        "general_rule": "When the file mainly changes prior terms, role should be delta.",
    },
    {
        "pattern": "An award letter or vendor disclosure statement references real procurement facts but does not carry the contract terms that govern performance.",
        "tempting_wrong_answer": "primary_document_role=operative or delta",
        "why_tempting": "It is procurement-relevant and may include identifiers, dates, or vendor names.",
        "why_wrong": "It provides context around the procurement process rather than the operative or changing contract instrument.",
        "general_rule": "If the file mainly informs, approves, or documents compliance, role should be context.",
    },
)


CHANGE_KIND_LEARNINGS = (
    {
        "pattern": "A renewal letter extends time or continues service into a new term.",
        "tempting_wrong_answer": "change_kind=amendment",
        "why_tempting": "The document may still use general amendment language.",
        "why_wrong": "The main change being made is continuation or extension of term.",
        "general_rule": "Use renewal when the dominant change is term continuation or extension.",
    },
    {
        "pattern": "A modification changes scope, clauses, or administrative terms without primarily extending the term.",
        "tempting_wrong_answer": "change_kind=renewal",
        "why_tempting": "The file may mention existing term dates or future periods.",
        "why_wrong": "The dominant change is still a general amendment/modification.",
        "general_rule": "Use amendment for general modifications unless renewal or pure pricing change is clearly dominant.",
    },
    {
        "pattern": "A repricing letter or updated schedule mainly changes rates or compensation.",
        "tempting_wrong_answer": "change_kind=amendment",
        "why_tempting": "Pricing updates are often documented as amendments.",
        "why_wrong": "The practical change type is pricing-specific, which is more useful for downstream routing.",
        "general_rule": "Use pricing_update when the primary delta is a rate or compensation revision.",
    },
    {
        "pattern": "A letter both renews a term and approves a specific price increase, but the document is framed primarily as a price increase notice or rate approval.",
        "tempting_wrong_answer": "change_kind=renewal because the file mentions a renewal period.",
        "why_tempting": "The document may extend the contract term while also revising pricing.",
        "why_wrong": "If the document's dominant business purpose is approving revised pricing, downstream routing is better served by pricing_update.",
        "general_rule": "When renewal and pricing both appear, choose the dominant delta stated by the document. If the file is primarily a price increase / repricing notice, use pricing_update.",
    },
)


def render_learning_block(title: str, learnings: tuple[dict[str, str], ...]) -> str:
    """Render one structured learning block for prompt inclusion."""
    lines = [title]
    for item in learnings:
        lines.extend(
            [
                f"- Pattern: {item['pattern']}",
                f"  Tempting wrong answer: {item['tempting_wrong_answer']}",
                f"  Why tempting: {item['why_tempting']}",
                f"  Why wrong: {item['why_wrong']}",
                f"  General rule: {item['general_rule']}",
            ]
        )
    return "\n".join(lines)


def classification_system_prompt() -> str:
    """Return the system prompt for document-level classification."""
    primary_artifact_learnings = render_learning_block(
        "Primary artifact learnings:",
        PRIMARY_ARTIFACT_LEARNINGS,
    )
    procurement_stage_learnings = render_learning_block(
        "procurement_stage learnings:",
        PROCUREMENT_STAGE_LEARNINGS,
    )
    document_role_learnings = render_learning_block(
        "primary_document_role learnings:",
        DOCUMENT_ROLE_LEARNINGS,
    )
    change_kind_learnings = render_learning_block(
        "change_kind learnings:",
        CHANGE_KIND_LEARNINGS,
    )
    return (
        "Task:\n"
        "Classify one procurement-related document into a stable two-axis schema used for business understanding and downstream extraction routing.\n"
        "Use the document content exactly as provided. Do not invent missing facts. Prefer explicit uncertainty over overclaiming.\n"
        "Return exactly one JSON object and no surrounding prose.\n"
        "\n"
        "Core instructions:\n"
        "- Solve the task in a strict sequence.\n"
        "- First determine the primary artifact in the file.\n"
        "- Then classify procurement_stage.\n"
        "- Then classify primary_document_role.\n"
        "- Then set change_kind only if the file is active_change + delta.\n"
        "- Use the whole file to understand context, but do not average all artifacts together. The final labels must follow the primary artifact.\n"
        "- If materially different secondary artifacts are present, preserve that fact in warnings and evidence rather than changing the main labels.\n"
        "- Prefer null, unclear, or a warning over an aggressive guess.\n"
        "\n"
        "Output fields:\n"
        f"- procurement_stage must be one of: {_enum_values(ProcurementStage)}.\n"
        f"- primary_document_role must be one of: {_enum_values(DocumentRole)}.\n"
        f"- change_kind must be one of: {_enum_values(ChangeKind)} or null.\n"
        "- evidence_pages must be a short list of integer page numbers only.\n"
        "- evidence items must contain label, snippet, and page_number.\n"
        "- warnings should capture ambiguity, mixed artifacts, weak OCR, or notable secondary artifacts.\n"
        "- status is not part of the reasoning; include it only because the output contract requires it.\n"
        "\n"
        "Step 1: identify the primary artifact.\n"
        "- Read the file holistically, but decide what the file is mainly about.\n"
        "- Give extra weight to the title, opening page, explicit document labels, execution/signature sections, and repeated framing language.\n"
        "- If the file contains a clear renewal notice, amendment, modification, signed agreement, SOW, task order, award letter, or disclosure form, that primary artifact should usually control classification.\n"
        "- If the file contains attachments of another type, treat them as secondary unless they clearly displace the apparent primary artifact.\n"
        "- In the rationale, explain what you decided the primary artifact is.\n"
        "\n"
        "Step 2: decide procurement_stage.\n"
        "- Ask: what procurement event or phase is the primary artifact mainly about?\n"
        "- Use sourcing for solicitations, proposals, quotes, bids, or procurement-seeking activity.\n"
        "- Use award for award notices, intent letters, approvals, or selection-stage artifacts.\n"
        "- Use contracting for signed agreements, signed SOWs, task orders, work orders, or other operative instruments that establish performance terms.\n"
        "- Use active_change for amendments, renewals, extensions, repricing instruments, or other documents whose main job is to change an existing relationship.\n"
        "- Use compliance for vendor disclosures, ethics/campaign/conflict forms, insurance/compliance certifications, or similar support paperwork.\n"
        "- Use unclear only when no stage can be chosen safely.\n"
        "- Do not let referenced artifacts override the stage of the primary artifact.\n"
        "\n"
        "Step 3: decide primary_document_role.\n"
        "- Ask: within that stage, is the primary artifact operative, delta, or context?\n"
        "- Use operative when the file carries the actual contract substance for that stage.\n"
        "- Use delta when the file primarily changes an existing procurement artifact.\n"
        "- Use context when the file mainly informs, approves, documents compliance, or supplies background rather than carrying the operative or changing contract terms.\n"
        "- A signed subordinate project instrument can still be operative.\n"
        "- A renewal, amendment, extension, or modification should usually be delta.\n"
        "- Award letters and compliance forms should usually be context.\n"
        "\n"
        "Step 4: decide change_kind only if procurement_stage=active_change and primary_document_role=delta.\n"
        "- Use renewal when the dominant change is extending or continuing the term.\n"
        "- Use amendment when the dominant change is a general modification to scope, clauses, administrative terms, or other non-renewal contract changes.\n"
        "- Use pricing_update when the dominant change is rates, fees, compensation, or pricing schedule.\n"
        "- If both renewal and pricing appear, choose the dominant business change the document is mainly communicating.\n"
        "- A document titled or framed as a price increase letter, repricing notice, or rate adjustment should usually be pricing_update even if it also references the renewal period.\n"
        "- Otherwise set change_kind to null.\n"
        "\n"
        "Step 5: record secondary-artifact effects.\n"
        "- If the file includes attached disclosures, proposals, resolutions, exhibits, or support pages, mention that in warnings.\n"
        "- Secondary artifact warnings should not change the main labels unless the supposed secondary artifact is actually the dominant artifact in the file.\n"
        "- Good warning examples include: mixed_bundle, attached_vendor_disclosure, attached_supporting_resolution, weak_primary_artifact_signal.\n"
        "\n"
        "Tie-break rules:\n"
        "- If a renewal, modification, or amendment is the primary artifact and a vendor disclosure form is merely attached, classify the file as active_change/delta and add a warning about the disclosure attachment.\n"
        "- If a standalone disclosure or compliance form contains labels such as contract, renewal, bid, or SOI, classify it as compliance/context unless the file itself clearly stops being a form and becomes another artifact.\n"
        "- If a signed SOW, task order, work order, or executed project agreement is the dominant artifact, classify it as contracting/operative even if it is governed by a master agreement.\n"
        "- If an award notice mentions contract details but does not itself contain the executed operative terms, classify it as award/context.\n"
        "- If evidence is split and no dominant artifact can be identified safely, use procurement_stage=unclear, choose the least committal role justified by the text, and explain the ambiguity.\n"
        "\n"
        f"{primary_artifact_learnings}\n"
        "\n"
        f"{procurement_stage_learnings}\n"
        "\n"
        f"{document_role_learnings}\n"
        "\n"
        f"{change_kind_learnings}\n"
        "\n"
        "Confidence guidance:\n"
        "- Use 0.95-1.00 only when the primary artifact is clear and the chosen labels follow directly from clean text.\n"
        "- Use 0.80-0.94 when the answer is strong but mixed artifacts, OCR issues, or mild ambiguity remain.\n"
        "- Use 0.00-0.79 when the primary artifact is uncertain, signals conflict, or structure/OCR materially weakens the judgment.\n"
        "- Penalize confidence when warnings indicate mixed artifacts, weak page-1 signal, or conflicting evidence.\n"
        "\n"
        "Output contract:\n"
        "{\n"
        '  "doc_id": "...",\n'
        '  "source_filename": "...",\n'
        '  "procurement_stage": "sourcing|award|contracting|active_change|compliance|unclear",\n'
        '  "primary_document_role": "operative|delta|context",\n'
        '  "change_kind": "renewal|amendment|pricing_update" or null,\n'
        '  "confidence": 0.0,\n'
        '  "evidence_pages": [1, 2],\n'
        '  "rationale": "...",\n'
        '  "warnings": [],\n'
        '  "evidence": [{"label": "...", "snippet": "...", "page_number": 1}],\n'
        '  "status": {"status": "completed", "version": "0.1.0", "error": null, "warnings": [], "updated_at": "2026-01-01T00:00:00+00:00"}\n'
        "}\n"
        "The updated_at value may be any valid ISO timestamp."
    )
