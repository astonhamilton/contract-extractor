from __future__ import annotations

from pathlib import Path


def _corpus_index_dump_path() -> Path:
    """Return the CSV file that stores the embedded corpus map."""
    return _prompt_parts_dir() / "corpus_index.csv"


def _prompt_parts_dir() -> Path:
    """Return the directory that stores corpus assistant prompt fragments."""
    return Path(__file__).with_name("prompt_parts")


def _read_part(name: str) -> str:
    """Read one corpus assistant prompt fragment from disk."""
    return (_prompt_parts_dir() / name).read_text(encoding="utf-8").strip()


def system_prompt() -> str:
    """Return the corpus assistant system prompt with embedded corpus-map context."""
    sections = [
        _read_part("00_identity.md"),
        _read_part("10_tools_and_evidence_model.md"),
        _read_part("20_question_type_index.md"),
        _read_part("question_types/governing_document_identification/workflow.md"),
        _read_part("question_types/governing_document_identification/learnings.md"),
        _read_part("30_answering_users.md"),
        _read_part("90_corpus_reference.md"),
    ]
    prompt = "\n\n".join(section for section in sections if section)
    corpus_index_dump = _corpus_index_dump_path().read_text(encoding="utf-8").strip()
    return prompt.replace("{{CORPUS_INDEX_DUMP}}", corpus_index_dump)
