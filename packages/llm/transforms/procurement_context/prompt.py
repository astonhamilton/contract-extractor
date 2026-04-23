from __future__ import annotations

from packages.schemas import ProcurementCategory


def _enum_values(enum_type) -> str:
    """Return a comma-separated list of enum values for prompt inclusion."""
    return ", ".join(member.value for member in enum_type)


LEARNINGS_FROM_MISTAKES = (
    {
        "pattern": "Vendor disclosure form mentions contract period, vendor, and identifiers",
        "tempting_wrong_answer": "Treat it as non-procurement because it is only compliance paperwork.",
        "why_tempting": "It is not the operative contract.",
        "why_wrong": "It still sits inside the procurement/vendor-contracting process and often carries valid buyer, seller, and identifier context.",
        "general_rule": "A supporting procurement document can still be a procurement document for this stage.",
    },
    {
        "pattern": "Sourcewell or cooperative language is prominent",
        "tempting_wrong_answer": "Use Sourcewell or the cooperative entity as the buyer.",
        "why_tempting": "The cooperative vehicle is often more prominent than the local county buyer.",
        "why_wrong": "The cooperative is the sourcing path, not necessarily the local buyer.",
        "general_rule": "Do not use Sourcewell as buyer by default; look for the real local buyer, and if not visible leave buyer null and add a warning.",
    },
    {
        "pattern": "Award letter or resolution appears before the operative agreement",
        "tempting_wrong_answer": "Anchor buyer, seller, and subject only from the first page summary.",
        "why_tempting": "The first page may have the clearest headings.",
        "why_wrong": "Later pages may name the actual vendor relationship and procurement subject more precisely.",
        "general_rule": "Scan enough of the document to identify the dominant procurement relationship before finalizing the record.",
    },
    {
        "pattern": "Many numbers appear in one procurement file",
        "tempting_wrong_answer": "Capture every visible number as a key identifier.",
        "why_tempting": "Procurement files often contain several structured references.",
        "why_wrong": "Only a few of them materially anchor the procurement artifact.",
        "general_rule": "Capture only explicit high-signal identifiers tied to contract, solicitation, award, quote, or PO context.",
    },
    {
        "pattern": "Lease or facilities document does not look like a standard services contract",
        "tempting_wrong_answer": "Treat it as outside procurement context.",
        "why_tempting": "The form factor differs from ordinary vendor service agreements.",
        "why_wrong": "Leases and facilities arrangements can still be county procurement relationships with buyer, seller, subject, and identifiers.",
        "general_rule": "Classify the procurement relationship by what is being procured, not only by standard contract formatting.",
    },
)


def render_learnings_from_mistakes() -> str:
    """Render the example-based error-pattern section for the prompt."""
    lines: list[str] = ["Learnings from mistakes:"]
    for item in LEARNINGS_FROM_MISTAKES:
        lines.extend(
            [
                f"- Pattern: {item['pattern']}.",
                f"  Tempting wrong extraction: {item['tempting_wrong_answer']}",
                f"  Why tempting: {item['why_tempting']}",
                f"  Why wrong: {item['why_wrong']}",
                f"  General rule: {item['general_rule']}",
            ]
        )
    return "\n".join(lines)


def procurement_context_system_prompt() -> str:
    """Return the system prompt for procurement-context inference."""
    learnings = render_learnings_from_mistakes()
    return (
        "Task:\n"
        "Infer minimal procurement context for one normalized document from a procurement-heavy contract corpus.\n"
        "This is not a lifecycle-classification or full extraction task.\n"
        "Your job is to determine whether the document is part of a procurement/vendor-contracting process and, if so, identify the buyer, seller, subject, and broad category.\n"
        "Return exactly one JSON object and no surrounding prose.\n"
        "\n"
        "Core reading rules:\n"
        "- Identify the commercial/procurement relationship before trying to infer exact document type.\n"
        "- Prefer explicit party, subject, and identifier language over filename hints.\n"
        "- Keep the schema small and prefer null over weak inference.\n"
        "- A supporting document can still be a procurement document for this stage.\n"
        "- If Sourcewell or another cooperative purchasing entity appears, do not use it as buyer by default. Look for the real local buyer; if you cannot find one, leave buyer null and explain via warnings/evidence.\n"
        "- Use document text, not corpus assumptions, to decide is_procurement_doc.\n"
        "\n"
        "Reading process:\n"
        "1. Decide whether the document is meaningfully part of a procurement/vendor relationship.\n"
        "2. Identify the buyer.\n"
        "3. Identify the seller/vendor/contractor/lessor.\n"
        "4. Summarize what is being bought.\n"
        "5. Choose a broad procurement category.\n"
        "6. Set warnings, evidence, and overall confidence.\n"
        "\n"
        "Field semantics:\n"
        "- is_procurement_doc: yes when the document clearly sits in a procurement/vendor-contracting workflow; no when it clearly does not; unclear when evidence is too weak or noisy.\n"
        "- buyer: the primary buying county/entity/department visible in the document.\n"
        "- seller: the primary external vendor/contractor/consultant/lessor visible in the document.\n"
        "- procurement_subject_summary: a short plain-language summary of what is being bought. Do not just repeat 'services' or the filename.\n"
        f"- procurement_category: one of {_enum_values(ProcurementCategory)}.\n"
        "- Choose the category by purchase subject, not by document form.\n"
        "- warnings should capture ambiguity or important watchouts, such as cooperative context with no explicit local buyer.\n"
        "- evidence should back the procurement gate plus buyer/seller/subject when available.\n"
        "\n"
        "Conflict resolution:\n"
        "- If many parties appear, choose the buyer and seller most central to the procurement relationship.\n"
        "- If the file is a mixed bundle, use the dominant procurement relationship visible in the file and add a warning when helpful.\n"
        "- If category is ambiguous, use the coarsest safe category rather than overfitting.\n"
        "- If Sourcewell/cooperative language is visible but the real local buyer is not explicit, leave buyer null and use warnings/evidence to explain why.\n"
        "\n"
        f"{learnings}\n"
        "\n"
        "Confidence guidance:\n"
        "- Use 0.95-1.00 only when procurement status, buyer, seller, subject, and category are strongly supported.\n"
        "- Use 0.80-0.94 when the procurement frame is strong but one or two fields remain weak.\n"
        "- Use below 0.80 when procurement status, party roles, or subject are materially unclear.\n"
        "- Lower confidence for OCR noise, mixed bundles, missing buyer/seller, vague subject matter, and cooperative documents where the local buyer is not explicit.\n"
        "\n"
        "Output contract:\n"
        "{\n"
        '  "doc_id": "...",\n'
        '  "source_filename": "...",\n'
        '  "is_procurement_doc": "yes|no|unclear",\n'
        '  "buyer": null,\n'
        '  "seller": null,\n'
        '  "procurement_subject_summary": null,\n'
        f'  "procurement_category": "{ProcurementCategory.PROFESSIONAL_SERVICES.value}|{ProcurementCategory.SOFTWARE_IT.value}|{ProcurementCategory.MAINTENANCE_OPERATIONS.value}|{ProcurementCategory.ENGINEERING_CONSTRUCTION.value}|{ProcurementCategory.BEHAVIORAL_HEALTH.value}|{ProcurementCategory.EQUIPMENT.value}|{ProcurementCategory.LEASE.value}|{ProcurementCategory.OTHER.value}|null",\n'
        '  "confidence": 0.0,\n'
        '  "warnings": [],\n'
        '  "evidence": [{"label": "...", "snippet": "...", "page_number": 1}],\n'
        '  "status": {"status": "completed", "version": "0.1.0", "error": null, "warnings": [], "updated_at": "2026-01-01T00:00:00+00:00"}\n'
        "}\n"
        "Use null instead of made-up values. The updated_at value may be any valid ISO timestamp."
    )
