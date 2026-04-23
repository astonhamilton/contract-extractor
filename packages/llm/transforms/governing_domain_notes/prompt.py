from __future__ import annotations

from pathlib import Path
from typing import Literal


GoverningNotesDomain = Literal[
    "identity",
    "parties",
    "subject",
    "term",
    "economics",
    "controls",
    "quality",
]

ALL_GOVERNING_NOTES_DOMAINS: tuple[GoverningNotesDomain, ...] = (
    "identity",
    "parties",
    "subject",
    "term",
    "economics",
    "controls",
    "quality",
)


IDENTITY_LEARNINGS = (
    {
        "pattern": "Operative agreement identifies itself clearly while related procurement materials are also referenced",
        "example": "Example: a professional services agreement can name itself as Agreement #25158 while also listing a BAFO, proposal, and RFP in an order-of-precedence clause.",
        "tempting_wrong_answer": "Treat the procurement-side material as the document's primary identity or leave identity vague because multiple materials are named.",
        "why_tempting": "The related materials are prominent and look more detailed than the base agreement.",
        "why_wrong": "The governing artifact still identifies itself directly, and that should anchor the identity notes.",
        "general_rule": "When the agreement explicitly states its own title or identifier, capture that first and then explain how other materials are linked.",
    },
)

PARTIES_LEARNINGS = (
    {
        "pattern": "Main parties are explicit, but other entities appear in support or oversight roles",
        "example": "Example: a governing agreement may clearly name the County and consultant while also mentioning approving agencies, departments, or proposal authors elsewhere in the packet.",
        "tempting_wrong_answer": "Blend all named organizations into the parties answer as if they were all principal parties.",
        "why_tempting": "All of the names are visible in the same file and can look equally important at first pass.",
        "why_wrong": "The parties notes should describe the principal contract-side organizations first and only mention other entities when they materially affect the operative relationship.",
        "general_rule": "Anchor the parties notes in the recital and signature block, then mention other entities only when their role materially matters.",
    },
)

SUBJECT_LEARNINGS = (
    {
        "pattern": "Operative agreement states core facts, while deeper detail lives in incorporated materials",
        "example": "Example: a professional services agreement can clearly state the title, parties, fee, and effective-term structure on pages 1-2 while detailed scope or pricing sits in a BAFO or proposal appendix.",
        "tempting_wrong_answer": "Leave the subject notes thin or empty because the richest detail appears in the incorporated material.",
        "why_tempting": "The deeper attachment has more words and looks like the better source for a summary.",
        "why_wrong": "The governing agreement still states important operative facts that should be captured now, even if deeper detail is deferred to incorporated material.",
        "general_rule": "Capture the agreement-level service or product description in the subject notes and then explain when deeper scope detail appears to be deferred to incorporated material.",
    },
)

TERM_LEARNINGS = (
    {
        "pattern": "Agreement gives a project-completion term structure rather than crisp start/end dates",
        "example": "Example: the agreement may say it is effective from execution through project completion, projected to take 12-18 months, with a short extension option for negotiating a replacement agreement.",
        "tempting_wrong_answer": "Produce a vague term note or skip the term note because there is no neat normalized start/end date pair.",
        "why_tempting": "The model is looking for exact dates and can treat nuanced term language as incomplete.",
        "why_wrong": "The term note should explain the operative term structure in prose even when the contract does not give a simple date pair.",
        "general_rule": "When the agreement describes term structure narratively, explain that structure directly rather than zeroing out the term answer.",
    },
)

ECONOMICS_LEARNINGS = (
    {
        "pattern": "Agreement states a clear fee or payment mechanic while detailed price sheets live elsewhere",
        "example": "Example: the base agreement may say the County will pay a fee of $108,340 and allow monthly invoicing, while the deeper BAFO price sheet sits in incorporated material.",
        "tempting_wrong_answer": "Leave economics thin or empty because the detailed schedule is not visible in the operative pages.",
        "why_tempting": "The richer pricing detail lives elsewhere, so the agreement-level fee can feel incomplete.",
        "why_wrong": "An explicit fee and payment mechanic in the operative agreement are still important economics answers and should be captured.",
        "general_rule": "If the governing agreement itself states the fee, cap, or payment cadence, explain those economics directly even when lower-level pricing detail lives elsewhere.",
    },
)

CONTROLS_LEARNINGS = (
    {
        "pattern": "Support paperwork or incorporated materials contain many control-like details",
        "example": "Example: a packet may include insurance schedules, disclosure forms, or support exhibits with extra detail behind the main agreement.",
        "tempting_wrong_answer": "Let the support material dominate the controls answer even when the governing agreement already states the operative insurance, termination, or compliance structure.",
        "why_tempting": "Support material often contains long checklists that look easier to summarize than the base agreement.",
        "why_wrong": "The controls notes should still answer from the operative artifact first, using support material only where it clearly matters.",
        "general_rule": "Summarize the operative controls from the governing agreement first and only pull in support-material detail when it is clearly operative or necessary to explain the caveat.",
    },
)

QUALITY_LEARNINGS = (
    {
        "pattern": "Mixed packet with support material behind a signed agreement",
        "example": "Example: a resolution, proposal, or disclosure form may appear in the same PDF behind an executed agreement.",
        "tempting_wrong_answer": "Blend the entire packet into one undifferentiated answer instead of isolating the caveat.",
        "why_tempting": "The packet reads like one file and the support material may be more descriptive than the agreement itself.",
        "why_wrong": "The quality note should explain the caveat while the domain answers stay anchored to the operative artifact.",
        "general_rule": "Use the quality note to explain packet complexity or incorporated-material dependence without letting that erase the domain answers.",
    },
)


def render_learning_block(title: str, learnings: tuple[dict[str, str], ...]) -> str:
    """Render one grouped learning block for prompt inclusion."""
    lines = [title]
    for item in learnings:
        lines.extend(
            [
                f"- Pattern: {item['pattern']}",
                f"  Example from corpus: {item['example']}",
                f"  Tempting wrong answer: {item['tempting_wrong_answer']}",
                f"  Why tempting: {item['why_tempting']}",
                f"  Why wrong: {item['why_wrong']}",
                f"  General rule: {item['general_rule']}",
            ]
        )
    return "\n".join(lines)


def _prompt_parts_dir() -> Path:
    """Return the directory that stores Markdown prompt fragments."""
    return Path(__file__).with_name("prompt_parts")


def _read_part(name: str) -> str:
    """Read one Markdown fragment from disk."""
    return (_prompt_parts_dir() / name).read_text(encoding="utf-8").strip()


def _normalized_domains(
    domains: tuple[GoverningNotesDomain, ...] | list[GoverningNotesDomain] | None,
) -> tuple[GoverningNotesDomain, ...]:
    """Normalize and validate a requested domain subset."""
    if domains is None:
        return ALL_GOVERNING_NOTES_DOMAINS

    normalized = tuple(domains)
    invalid = sorted(set(normalized) - set(ALL_GOVERNING_NOTES_DOMAINS))
    if invalid:
        raise ValueError(f"Unsupported governing note domains requested: {invalid}")
    if not normalized:
        raise ValueError("At least one governing note domain must be requested.")
    return normalized


def _domain_section_parts(
    domains: tuple[GoverningNotesDomain, ...],
) -> list[str]:
    """Return Markdown prompt sections for the requested domains."""
    part_map: dict[GoverningNotesDomain, tuple[str, str]] = {
        "identity": ("10_identity.md", "11_identity_learnings.md"),
        "parties": ("20_parties.md", "21_parties_learnings.md"),
        "subject": ("30_subject.md", "31_subject_learnings.md"),
        "term": ("40_term.md", "41_term_learnings.md"),
        "economics": ("50_economics.md", "51_economics_learnings.md"),
        "controls": ("60_controls.md", "61_controls_learnings.md"),
        "quality": ("70_quality.md", "71_quality_learnings.md"),
    }
    sections: list[str] = []
    for domain in domains:
        prompt_part, learning_part = part_map[domain]
        sections.append(_read_part(prompt_part))
        sections.append(_read_part(learning_part))
    return sections


def _output_contract_section(domains: tuple[GoverningNotesDomain, ...]) -> str:
    """Return an output-contract section containing only requested domains."""
    domain_contracts: dict[GoverningNotesDomain, str] = {
        "identity": (
            '  "identity": {\n'
            '    "what_this_document_is": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]},\n'
            '    "how_it_identifies_itself": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]},\n'
            '    "linked_documents_or_materials": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]}\n'
            "  }"
        ),
        "parties": (
            '  "parties": {\n'
            '    "who_the_main_parties_are": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]},\n'
            '    "how_their_roles_are_described": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]},\n'
            '    "other_material_entities": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]}\n'
            "  }"
        ),
        "subject": (
            '  "subject": {\n'
            '    "what_is_being_bought_or_governed": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]},\n'
            '    "what_scope_or_deliverables_are_described": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]}\n'
            "  }"
        ),
        "term": (
            '  "term": {\n'
            '    "when_it_takes_effect_and_how_long_it_runs": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]},\n'
            '    "how_renewal_or_extension_works": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]}\n'
            "  }"
        ),
        "economics": (
            '  "economics": {\n'
            '    "how_pricing_works": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]},\n'
            '    "what_total_fee_or_cap_language_is_explicit": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]},\n'
            '    "how_payment_is_described": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]}\n'
            "  }"
        ),
        "controls": (
            '  "controls": {\n'
            '    "how_termination_or_exit_works": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]},\n'
            '    "what_insurance_or_risk_requirements_apply": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]},\n'
            '    "what_performance_or_compliance_obligations_matter": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]}\n'
            "  }"
        ),
        "quality": (
            '  "quality": {\n'
            '    "important_caveats_or_ambiguities": {"answer": null, "citations": [{"page_number": 1, "snippet": "..."}]}\n'
            "  }"
        ),
    }
    selected = [domain_contracts[domain] for domain in domains]
    return "Output contract:\n{\n" + ",\n".join(selected) + "\n}\nUse null instead of made-up values."


def governing_domain_notes_system_prompt(
    domains: tuple[GoverningNotesDomain, ...] | list[GoverningNotesDomain] | None = None,
) -> str:
    """Assemble the governing domain-notes prompt from Markdown fragments."""
    domains = _normalized_domains(domains)
    replacements = {
        "{{IDENTITY_LEARNINGS}}": render_learning_block(
            "Identity learnings:", IDENTITY_LEARNINGS
        ),
        "{{PARTIES_LEARNINGS}}": render_learning_block(
            "Parties learnings:", PARTIES_LEARNINGS
        ),
        "{{SUBJECT_LEARNINGS}}": render_learning_block(
            "Subject learnings:", SUBJECT_LEARNINGS
        ),
        "{{TERM_LEARNINGS}}": render_learning_block("Term learnings:", TERM_LEARNINGS),
        "{{ECONOMICS_LEARNINGS}}": render_learning_block(
            "Economics learnings:", ECONOMICS_LEARNINGS
        ),
        "{{CONTROLS_LEARNINGS}}": render_learning_block(
            "Controls learnings:", CONTROLS_LEARNINGS
        ),
        "{{QUALITY_LEARNINGS}}": render_learning_block(
            "Quality learnings:", QUALITY_LEARNINGS
        ),
    }
    sections = [
        _read_part("00_preamble.md"),
        *_domain_section_parts(domains),
        _output_contract_section(domains),
    ]
    prompt = "\n\n".join(sections)
    for placeholder, rendered in replacements.items():
        prompt = prompt.replace(placeholder, rendered)
    return prompt
