from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from packages.llm.transforms.governing_domain_notes.config import GoverningDomainNotesConfig
from packages.llm.transforms.governing_domain_notes.prompt import (
    GoverningNotesDomain,
    ALL_GOVERNING_NOTES_DOMAINS,
    governing_domain_notes_system_prompt,
)
from packages.llm.shared.task_runtime.capabilities import effective_reasoning_effort
from packages.llm.shared.task_runtime.content import read_optional_text
from packages.llm.shared.task_runtime.structured import completion_json_schema
from packages.llm.shared.strict_schema import enforce_openai_strict_required
from packages.schemas import (
    GoverningDomainNotes,
    GoverningDomainNotesInput,
    GoverningDomainNotesModelOutput,
    governing_domain_notes_subset_model,
)
from packages.schemas.common import ProcessingStatus, StageStatus


LOGGER = logging.getLogger(__name__)
EMPTY_STRUCTURED_CONTENT_MARKER = "returned empty string content"


@dataclass
class GoverningDomainNotesAdaptiveResult:
    """Execution metadata for adaptive governing-domain-notes runs."""

    attempted_domain_groups: list[tuple[GoverningNotesDomain, ...]] = field(
        default_factory=list
    )
    used_adaptive_split: bool = False


def usage_summary_from_debug_dir(
    debug_dir: Path, *, max_tokens: int
) -> dict[str, object]:
    """Summarize attempt usage and detect budget-exhaustion heuristics."""
    attempts: list[dict[str, object]] = []
    budget_exhausted = False

    for response_path in sorted(debug_dir.rglob("attempt_*_response.json")):
        response_payload = json.loads(response_path.read_text(encoding="utf-8"))
        response = response_payload.get("response")
        if not isinstance(response, dict):
            continue
        usage = response.get("usage")
        if not isinstance(usage, dict):
            continue
        choice_list = response.get("choices") or []
        content = None
        if isinstance(choice_list, list) and choice_list:
            first_choice = choice_list[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
        headers = response_payload.get("headers")
        if not isinstance(headers, dict):
            headers = {}
        completion_details = usage.get("completion_tokens_details")
        if not isinstance(completion_details, dict):
            completion_details = {}
        reasoning_tokens = completion_details.get("reasoning_tokens")
        completion_tokens = usage.get("completion_tokens")
        content_str = content if isinstance(content, str) else ""
        attempts.append(
            {
                "attempt": str(response_path.relative_to(debug_dir).with_suffix("")),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": completion_tokens,
                "reasoning_tokens": reasoning_tokens,
                "total_tokens": usage.get("total_tokens"),
                "content_length": len(content_str),
                "rate_limit_remaining_tokens": headers.get(
                    "x-ratelimit-remaining-tokens"
                ),
                "rate_limit_reset_tokens": headers.get("x-ratelimit-reset-tokens"),
                "request_id": headers.get("x-request-id"),
            }
        )
        if (
            isinstance(completion_tokens, int)
            and isinstance(reasoning_tokens, int)
            and completion_tokens >= max_tokens
            and reasoning_tokens >= max_tokens
            and not content_str
        ):
            budget_exhausted = True

    return {
        "attempts": attempts,
        "heuristics": {
            "likely_output_budget_exhausted_by_reasoning": budget_exhausted,
        },
    }


def _is_empty_structured_content_error(error: Exception) -> bool:
    """Return True when a structured completion failed only because content was empty."""
    return isinstance(error, ValueError) and EMPTY_STRUCTURED_CONTENT_MARKER in str(error)


def _split_domain_group(
    domains: tuple[GoverningNotesDomain, ...],
) -> list[tuple[GoverningNotesDomain, ...]]:
    """Split a domain group into smaller semantically coherent groups."""
    if len(domains) <= 1:
        return [domains]

    if domains == ALL_GOVERNING_NOTES_DOMAINS:
        preferred = [
            ("identity", "parties", "subject"),
            ("term", "economics", "controls", "quality"),
        ]
        return [group for group in preferred if group]

    midpoint = len(domains) // 2
    return [domains[:midpoint], domains[midpoint:]]


def _merge_domain_notes(
    base: GoverningDomainNotes,
    overlay: GoverningDomainNotes,
    *,
    domains: tuple[GoverningNotesDomain, ...],
) -> GoverningDomainNotes:
    """Merge selected domains from one note artifact into another."""
    payload = base.model_dump(mode="python")
    overlay_payload = overlay.model_dump(mode="python")
    for domain in domains:
        payload[domain] = overlay_payload[domain]
    return GoverningDomainNotes.model_validate(payload)


def build_governing_domain_notes_input(
    *,
    doc_id: str,
    source_filename: str,
    model: str,
    normalized_document_path: Path,
) -> GoverningDomainNotesInput:
    """Build the typed input contract for one governing domain-notes request."""
    return GoverningDomainNotesInput(
        doc_id=doc_id,
        source_filename=source_filename,
        model=model,
        normalized_document_path=str(normalized_document_path),
    )


def build_governing_domain_notes_user_content(
    request: GoverningDomainNotesInput,
) -> str:
    """Build the user payload for one governing domain-notes call."""
    normalized_text = read_optional_text(Path(request.normalized_document_path))
    if not normalized_text:
        raise FileNotFoundError(
            f"Normalized document input missing: {request.normalized_document_path}"
        )

    return "\n".join(
        [
            "Extract governing domain notes from this normalized document representation.",
            f"doc_id: {request.doc_id}",
            f"source_filename: {request.source_filename}",
            "",
            "Normalized document XML:",
            normalized_text,
        ]
    )


def completed_governing_domain_notes_status() -> StageStatus:
    """Return a completed status block for validated domain-notes outputs."""
    return StageStatus(status=ProcessingStatus.COMPLETED)


def run_governing_domain_notes(
    request: GoverningDomainNotesInput,
    config: GoverningDomainNotesConfig,
    *,
    domains: tuple[GoverningNotesDomain, ...] | None = None,
    debug_dump_dir: Path | None = None,
) -> GoverningDomainNotes:
    """Run one governing domain-notes call and return a validated artifact."""
    if domains is None:
        domains = ALL_GOVERNING_NOTES_DOMAINS
    LOGGER.info(
        "LLM governing domain notes | file=%s | input=%s | domains=%s | reasoning_effort=%s",
        request.source_filename,
        request.normalized_document_path,
        ",".join(domains),
        effective_reasoning_effort(config.model, config.reasoning_effort),
    )
    messages = [
        {"role": "system", "content": governing_domain_notes_system_prompt(domains)},
        {"role": "user", "content": build_governing_domain_notes_user_content(request)},
    ]
    subset_model = governing_domain_notes_subset_model(tuple(domains))
    schema = enforce_openai_strict_required(
        subset_model.model_json_schema()
    )
    payload = completion_json_schema(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        reasoning_effort=config.reasoning_effort,
        schema_name="governing_domain_notes",
        schema=schema,
        debug_dump_dir=str(debug_dump_dir) if debug_dump_dir is not None else None,
    )
    payload.pop("doc_id", None)
    payload.pop("source_filename", None)
    payload.pop("status", None)
    subset_output = subset_model.model_validate(payload)
    merged_payload = GoverningDomainNotesModelOutput().model_dump(mode="python")
    for domain in domains:
        merged_payload[domain] = getattr(subset_output, domain)
    model_output = GoverningDomainNotesModelOutput.model_validate(merged_payload)
    notes = GoverningDomainNotes(
        doc_id=request.doc_id,
        source_filename=request.source_filename,
        **model_output.model_dump(mode="python"),
        status=completed_governing_domain_notes_status(),
    )
    LOGGER.info("LLM governing domain notes complete | file=%s", request.source_filename)
    return notes


def run_governing_domain_notes_adaptive(
    request: GoverningDomainNotesInput,
    config: GoverningDomainNotesConfig,
    *,
    domains: tuple[GoverningNotesDomain, ...] | None = None,
    debug_dump_dir: Path | None = None,
) -> tuple[GoverningDomainNotes, GoverningDomainNotesAdaptiveResult]:
    """Run governing-domain-notes extraction with adaptive domain splitting."""
    if domains is None:
        domains = ALL_GOVERNING_NOTES_DOMAINS

    result = GoverningDomainNotesAdaptiveResult()

    def _run_group(
        group: tuple[GoverningNotesDomain, ...],
        group_debug_dir: Path | None,
    ) -> GoverningDomainNotes:
        result.attempted_domain_groups.append(group)
        try:
            return run_governing_domain_notes(
                request,
                config,
                domains=group,
                debug_dump_dir=group_debug_dir,
            )
        except Exception as error:
            if len(group) == 1 or not _is_empty_structured_content_error(error):
                raise
            if group_debug_dir is None:
                raise
            usage_summary = usage_summary_from_debug_dir(
                group_debug_dir, max_tokens=config.max_tokens
            )
            heuristics = usage_summary.get("heuristics")
            if not (
                isinstance(heuristics, dict)
                and heuristics.get("likely_output_budget_exhausted_by_reasoning") is True
            ):
                raise
            result.used_adaptive_split = True
            merged = GoverningDomainNotes(
                doc_id=request.doc_id,
                source_filename=request.source_filename,
                status=completed_governing_domain_notes_status(),
            )
            child_groups = _split_domain_group(group)
            for child_group in child_groups:
                child_name = "_".join(child_group)
                child_debug_dir = (
                    group_debug_dir / f"group_{child_name}"
                    if group_debug_dir is not None
                    else None
                )
                child_notes = _run_group(child_group, child_debug_dir)
                merged = _merge_domain_notes(
                    merged, child_notes, domains=child_group
                )
            return merged

    notes = _run_group(domains, debug_dump_dir)
    return notes, result
