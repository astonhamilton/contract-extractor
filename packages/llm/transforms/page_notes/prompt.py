from __future__ import annotations


PAGE_NOTES_LEARNINGS = (
    {
        "pattern": "Continuation page gets oversummarized",
        "example": "Example: a dense legal page clearly continues a clause that began earlier, but this page does not by itself show the whole clause.",
        "tempting_wrong_answer": "Write a broad clause summary as if the full operative rule is visible on this page.",
        "why_tempting": "The page looks important and contains dense clause text, so it feels safer to summarize the whole clause family.",
        "why_wrong": "A page note is page-local and should help later retrieval decide whether to open the raw page, not pretend to know adjacent pages.",
        "general_rule": "Summarize what is visible on the page and say when the page appears to continue a clause rather than inventing the full clause meaning.",
    },
    {
        "pattern": "Table page summarized too vaguely",
        "example": "Example: a page contains a pricing schedule, rate table, or equipment list, but the note says only 'contains table.'",
        "tempting_wrong_answer": "Use a generic summary because tables are dense and time-consuming to read.",
        "why_tempting": "A generic note is easy and feels safer than misreading the table.",
        "why_wrong": "The page note exists to improve retrieval; it should tell later systems whether the table is about pricing, rates, equipment, insurance, or another schedule.",
        "general_rule": "Identify the function of the table page, not just the fact that it is tabular.",
    },
    {
        "pattern": "Page inherits the document label instead of its own role",
        "example": "Example: a vendor disclosure page sits behind a governing agreement or renewal packet.",
        "tempting_wrong_answer": "Mark the page as operative or change-related just because the larger document is.",
        "why_tempting": "The packet is classified at the document level, so repeating that label feels consistent.",
        "why_wrong": "Page notes should describe page-local function. An attached disclosure form is still a compliance/supporting page.",
        "general_rule": "Choose page_role from the visible page function, not from the overall document classification.",
    },
)


def _render_learnings() -> str:
    """Render reusable page-notes learnings for prompt inclusion."""
    lines = ["Learnings from common mistakes:"]
    for item in PAGE_NOTES_LEARNINGS:
        lines.extend(
            [
                f"- Pattern: {item['pattern']}",
                f"  Example: {item['example']}",
                f"  Tempting wrong answer: {item['tempting_wrong_answer']}",
                f"  Why tempting: {item['why_tempting']}",
                f"  Why wrong: {item['why_wrong']}",
                f"  General rule: {item['general_rule']}",
            ]
        )
    return "\n".join(lines)


def page_notes_system_prompt() -> str:
    """Return the retrieval-oriented prompt for one page note."""
    return (
        "Task:\n"
        "Write one retrieval-oriented note for one page of a document.\n"
        "This is a page-local document-map task, not full extraction.\n"
        "Return exactly one JSON object and no surrounding prose.\n"
        "\n"
        "What this note is for:\n"
        "- Help a later system decide whether to open the raw page text.\n"
        "- Make the page easy to scan in a document map.\n"
        "- Preserve the highest-value retrieval handles without trying to normalize every fact.\n"
        "\n"
        "Core rules:\n"
        "- Stay page-local. Summarize only the visible page.\n"
        "- Prefer short, concrete prose over overfitted field extraction.\n"
        "- Do not invent content from adjacent pages.\n"
        "- Do not restate the whole document.\n"
        "- Capture enough detail to understand why the page matters.\n"
        "- Prefer null or [] over weak inference.\n"
        "- Page role should describe the visible page function, not blindly inherit the document's overall classification.\n"
        "\n"
        "Decision steps:\n"
        "1. Identify the page's dominant visible function.\n"
        "   - If a page combines a cover/header with real opening agreement terms, parties, scope, or term language, prefer the operative role over cover_or_index.\n"
        "2. Write a short summary of what is on the page.\n"
        "3. Capture the most useful retrieval handles in key_terms.\n"
        "4. Add a few relevance_tags only when strongly supported by the page.\n"
        "5. Add warnings only when they would actually help a later reader.\n"
        "\n"
        "Field instructions:\n"
        "- page_role: one of operative_clause, change_clause, pricing_or_rate_table, signature_or_execution, compliance_or_disclosure, supporting_context, cover_or_index, low_value_or_boilerplate, unclear.\n"
        "- summary: 1-3 sentences describing the visible page. Mention the page's function and the most important visible content.\n"
        "- key_terms: a compact mixed list of the most useful retrieval handles such as vendor names, county units, contract numbers, amendment labels, major dates, major amounts, exhibit labels, or section labels.\n"
        "- key_terms should usually contain only the highest-signal handles visible on the page, not every name or number.\n"
        "- Avoid full street addresses, boilerplate legal citations, and low-value details unless they are clearly needed for later page retrieval.\n"
        "- Avoid individual contact names or signers unless they are the clearest retrieval handle on the page.\n"
        "- Prefer short handles like 'RFP#010720', 'Contract #22053', 'Sourcewell', 'annual installment', or 'termination of purchase orders' over long copied strings.\n"
        "- relevance_tags: optional small list from governing, change, pricing, term, parties, compliance, procurement_history, signature, low_value.\n"
        "- warnings: use for OCR weakness, page likely continues another clause, table-heavy page may need raw review, low standalone meaning, or ambiguous role.\n"
        "\n"
        "Keep these boundaries:\n"
        "- key_terms is flexible and mixed; do not split it into entities/dates/money/identifiers.\n"
        "- summary should do most of the semantic work.\n"
        "- key_terms should complement the summary, not duplicate every detail already stated there.\n"
        "- Do not add citations. The page itself is the citation boundary.\n"
        "\n"
        f"{_render_learnings()}\n"
        "\n"
        "Output contract:\n"
        "{\n"
        '  "page_role": "operative_clause|change_clause|pricing_or_rate_table|signature_or_execution|compliance_or_disclosure|supporting_context|cover_or_index|low_value_or_boilerplate|unclear",\n'
        '  "summary": null,\n'
        '  "key_terms": [],\n'
        '  "relevance_tags": ["governing|change|pricing|term|parties|compliance|procurement_history|signature|low_value"],\n'
        '  "warnings": []\n'
        "}\n"
        "Use null instead of made-up detail."
    )
