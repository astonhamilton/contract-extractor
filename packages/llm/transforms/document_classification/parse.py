from __future__ import annotations

import json
import re

from packages.llm.transforms.document_classification.coerce import coerce_document_classification_payload
from packages.schemas import DocumentClassification, completed_classification_status


JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(text: str) -> dict[str, object]:
    """Extract the first JSON object from model output."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = JSON_OBJECT_RE.search(stripped)
        if not match:
            raise
        return json.loads(match.group(0))


def parse_document_classification(text: str) -> DocumentClassification:
    """Parse and validate a document classification from model JSON output."""
    payload = extract_json_object(text)
    payload = coerce_document_classification_payload(payload)
    classification = DocumentClassification.model_validate(payload)
    return classification.model_copy(update={"status": completed_classification_status()})
