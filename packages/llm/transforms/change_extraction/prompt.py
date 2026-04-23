from __future__ import annotations

from pathlib import Path


TARGET_ARTIFACT_LEARNINGS = (
    {
        "pattern": "Proposal or quote identifier appears near amendment language",
        "tempting_wrong_answer": "Treat the proposal/quote id as the target artifact being changed.",
        "why_tempting": "It is structured, prominent, and often appears near pricing language.",
        "why_wrong": "The target artifact should be the agreement, contract, SOW, or work order the change actually modifies.",
        "general_rule": "Use proposal/quote references as context unless the change language explicitly says that artifact is the thing being amended.",
    },
    {
        "pattern": "Mixed file with renewal letter plus disclosure/support pages",
        "tempting_wrong_answer": "Use the support pages to define what the change targets.",
        "why_tempting": "The support pages repeat vendor names, dates, and identifiers.",
        "why_wrong": "The operative target should come from the signed change instrument first.",
        "general_rule": "Anchor target-artifact notes to the operative change language, not attached support paperwork.",
    },
)

CHANGE_LEARNINGS = (
    {
        "pattern": "Amendment changes several things at once",
        "tempting_wrong_answer": "Summarize only the easiest visible dimension, such as term extension.",
        "why_tempting": "Titles and headings often foreground one dimension while burying others in body text.",
        "why_wrong": "A useful change note needs to reflect all explicit operative deltas.",
        "general_rule": "If several operative themes change, capture them in change.answer and use only the smallest useful set of coarse dimensions.",
    },
    {
        "pattern": "Renewal letter includes COI or disclosure submission instructions",
        "tempting_wrong_answer": "Add control dimensions just because the packet asks for updated forms or says the letter is formal notice to renew.",
        "why_tempting": "Those instructions are visible and operationally real, especially in vendor-renewal letters.",
        "why_wrong": "The core operative change is usually term renewal; support paperwork or formal-notice phrasing does not by itself mean notice mechanics changed.",
        "general_rule": "Keep dimensions on the operative contract change itself; ancillary renewal paperwork should usually stay in change.answer or warnings without becoming a separate dimension.",
    },
    {
        "pattern": "Instrument asks for supporting paperwork but does not amend any administrative contract term",
        "tempting_wrong_answer": "Use the control dimension because the document includes insurance, disclosure, or vendor follow-up instructions.",
        "why_tempting": "Those items look administrative in an everyday sense and are often near the operative renewal or amendment language.",
        "why_wrong": "The control dimension is for actual amended control/process mechanics, not for requested supporting paperwork that accompanies the change packet.",
        "general_rule": "Only use control when the instrument itself changes notice, reporting, invoicing, approvals, compliance, submission, or similar process mechanics.",
    },
    {
        "pattern": "Amendment assigns the agreement or incorporates an exhibit/addendum",
        "tempting_wrong_answer": "Tag control because assignment or exhibit incorporation feels like back-office contract administration.",
        "why_tempting": "These instruments often mix assignment language, incorporated requirements, scope text, and pricing in one amendment.",
        "why_wrong": "Assignment and incorporation are not automatically control mechanics; they usually matter because they change party identity, obligations, scope context, or compliance context.",
        "general_rule": "Do not use control for assignment or incorporated exhibits unless the instrument explicitly changes notice, reporting, billing, submission, or similar process mechanics.",
    },
    {
        "pattern": "Process/control language is present but may only be supporting context",
        "tempting_wrong_answer": "Tag control whenever the document mentions invoicing, reporting, insurance, compliance, or support instructions.",
        "why_tempting": "Control/process language often appears near the operative amendment text.",
        "why_wrong": "Over-tagging makes dimensions noisy and less useful for retrieval.",
        "general_rule": "Use control only for actual amended control/process mechanics such as invoicing, reporting, audit, approvals, compliance, notice, or submissions. Supporting instructions alone are not enough.",
    },
    {
        "pattern": "Renewal packet contains insurance evidence or disclosure reminders",
        "tempting_wrong_answer": "Use control because insurance/disclosure/document submission feels like compliance or administration.",
        "why_tempting": "Those requests sound operationally important and are often repeated near the signature or renewal language.",
        "why_wrong": "In this corpus they are usually supporting renewal instructions, not operative amendments to reporting, compliance, or admin mechanics.",
        "general_rule": "For simple renewals, updated COIs, insurance evidence, disclosure statements, or contact reminders should stay as secondary prose context or warnings unless the instrument explicitly amends a reporting, compliance, notice, or submission term.",
    },
    {
        "pattern": "Renewal letter says contractor must maintain or submit insurance certificate materials",
        "tempting_wrong_answer": "Tag control because insurance certificates and submission obligations sound like compliance mechanics.",
        "why_tempting": "The wording can sound mandatory and clause-like, especially when attached to renewal effectiveness.",
        "why_wrong": "In these renewal letters the operative legal change is still just term extension; the insurance instruction is packet support unless the contract's actual compliance or reporting mechanics are being amended.",
        "general_rule": "When a renewal letter extends the contract and carries forward existing terms, insurance-certificate maintenance or submission language should not create a control dimension by itself.",
    },
    {
        "pattern": "Pricing update states an anniversary period or contract year",
        "tempting_wrong_answer": "Add a term dimension because the new prices apply during a stated contract year or anniversary window.",
        "why_tempting": "The document names a date range and can look like it is setting a new term.",
        "why_wrong": "A pricing period is not necessarily a contract-period amendment.",
        "general_rule": "Do not add term just because repriced rates apply for a stated contract year, anniversary period, or effective date window unless the contract period itself is being extended or revised.",
    },
)

RESULTING_STATE_LEARNINGS = (
    {
        "pattern": "New state is only partially explicit",
        "tempting_wrong_answer": "Infer the full resulting state from background context or prior documents.",
        "why_tempting": "The intended result may seem obvious from the surrounding procurement history.",
        "why_wrong": "This pass should report only what the current change artifact explicitly establishes.",
        "general_rule": "Keep resulting_state.answer narrow and explicit; if only part of the new state is stated, say only that part.",
    },
    {
        "pattern": "Change mechanism is explicit but resulting amount/date is not",
        "tempting_wrong_answer": "Invent a final amount or date from nearby tables or prior values.",
        "why_tempting": "The mechanism strongly suggests what the result probably is.",
        "why_wrong": "Mechanism language is not the same as an explicit resulting state.",
        "general_rule": "Describe the mechanism in change.answer and leave resulting_state.answer sparse unless the post-change state is actually stated.",
    },
    {
        "pattern": "Document contains both specific revised terms and generic remaining-provisions boilerplate",
        "tempting_wrong_answer": "Use only the boilerplate clause as the resulting-state answer.",
        "why_tempting": "The remaining-provisions clause is a clean summary-looking sentence near the end of the instrument.",
        "why_wrong": "It loses the actual substantive new state established by the change.",
        "general_rule": "When specific resulting dates, fees, credits, scope removals, or obligations are explicit, summarize those first and treat remaining-provisions language as secondary context.",
    },
)

EVIDENCE_LEARNINGS = (
    {
        "pattern": "Operational scheduling notice appears near amendment language",
        "tempting_wrong_answer": "Treat the scheduling notice as the main contractual delta or formal notice change.",
        "why_tempting": "The phrase contains dates or notice language and looks clause-like.",
        "why_wrong": "Operational coordination language is not necessarily the operative contract change.",
        "general_rule": "Prefer linkage, main delta, resulting-state, and execution clauses over nearby operational logistics text.",
    },
    {
        "pattern": "OCR-heavy file with one or two legible operative clauses",
        "tempting_wrong_answer": "Spread confidence across the whole document as if all pages were equally clear.",
        "why_tempting": "A few clear clauses can make the whole record feel more complete than it is.",
        "why_wrong": "The note set should be honest about partial visibility.",
        "general_rule": "Use key_clauses and warnings to point to the specific usable passages and lower confidence when the rest of the artifact is weak.",
    },
)


def render_learning_block(title: str, learnings: tuple[dict[str, str], ...]) -> str:
    """Render one domain learning block for prompt inclusion."""
    lines = [title]
    for item in learnings:
        lines.extend(
            [
                f"- Pattern: {item['pattern']}",
                f"  Tempting wrong extraction: {item['tempting_wrong_answer']}",
                f"  Why tempting: {item['why_tempting']}",
                f"  Why wrong: {item['why_wrong']}",
                f"  General rule: {item['general_rule']}",
            ]
        )
    return "\n".join(lines)


def _prompt_parts_dir() -> Path:
    """Return the directory that stores change prompt fragments."""
    return Path(__file__).with_name("prompt_parts")


def _read_part(name: str) -> str:
    """Read one Markdown fragment from disk."""
    return (_prompt_parts_dir() / name).read_text(encoding="utf-8").strip()


def change_extraction_system_prompt() -> str:
    """Assemble the note-based change extraction prompt from Markdown fragments."""
    replacements = {
        "{{TARGET_ARTIFACT_LEARNINGS}}": render_learning_block(
            "Target artifact learnings:",
            TARGET_ARTIFACT_LEARNINGS,
        ),
        "{{CHANGE_LEARNINGS}}": render_learning_block(
            "Change learnings:",
            CHANGE_LEARNINGS,
        ),
        "{{RESULTING_STATE_LEARNINGS}}": render_learning_block(
            "Resulting-state learnings:",
            RESULTING_STATE_LEARNINGS,
        ),
        "{{EVIDENCE_LEARNINGS}}": render_learning_block(
            "Evidence learnings:",
            EVIDENCE_LEARNINGS,
        ),
    }
    sections = [
        _read_part("00_preamble.md"),
        _read_part("10_target_artifact.md"),
        _read_part("11_target_artifact_learnings.md"),
        _read_part("20_change.md"),
        _read_part("21_change_learnings.md"),
        _read_part("30_resulting_state.md"),
        _read_part("31_resulting_state_learnings.md"),
        _read_part("40_evidence.md"),
        _read_part("41_evidence_learnings.md"),
        _read_part("90_output_contract.md"),
    ]
    prompt = "\n\n".join(sections)
    for placeholder, rendered in replacements.items():
        prompt = prompt.replace(placeholder, rendered)
    return prompt
