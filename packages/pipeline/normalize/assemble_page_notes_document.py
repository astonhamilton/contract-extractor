from __future__ import annotations

from packages.schemas import PageNotesDocument


def xml_escape_attr(value: str) -> str:
    """Escape XML attribute content."""
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def cdata_wrap(text: str) -> str:
    """Wrap text in CDATA safely for XML output."""
    return f"<![CDATA[{text.replace(']]>', ']]]]><![CDATA[>')}]]>"


def normalized_page_notes_xml(page_notes: PageNotesDocument) -> str:
    """Assemble a document-level XML view over page notes."""
    page_blocks: list[str] = []
    for note in page_notes.page_notes:
        warnings = ",".join(note.warnings) if note.warnings else ""
        key_terms = "\n".join(
            f"        <term>{cdata_wrap(term)}</term>" for term in note.key_terms if term.strip()
        )
        relevance_tags = "\n".join(
            f'        <tag value="{xml_escape_attr(tag.value)}" />'
            for tag in note.relevance_tags
            if tag.value.strip()
        )
        lines = [
            f'    <page_note number="{note.page_number}" role="{xml_escape_attr(note.page_role.value if note.page_role else "unclear")}">',
            f"      <summary>{cdata_wrap(note.summary or '')}</summary>",
            f"      <warnings>{xml_escape_attr(warnings)}</warnings>",
            "      <key_terms>",
            key_terms,
            "      </key_terms>",
            "      <relevance_tags>",
            relevance_tags,
            "      </relevance_tags>",
            "    </page_note>",
        ]
        page_blocks.append("\n".join(lines))

    lines = [
        f'<page_notes_document doc_id="{xml_escape_attr(page_notes.doc_id)}">',
        "  <metadata>",
        f"    <source_filename>{xml_escape_attr(page_notes.source_filename)}</source_filename>",
        f"    <page_count>{len(page_notes.page_notes)}</page_count>",
        "  </metadata>",
        "  <page_notes>",
        "\n".join(page_blocks),
        "  </page_notes>",
        "</page_notes_document>",
    ]
    return "\n".join(lines) + "\n"
