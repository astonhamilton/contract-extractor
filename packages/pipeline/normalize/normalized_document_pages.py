from __future__ import annotations

import html
import re
from pathlib import Path


PAGE_BLOCK_RE = re.compile(r"<page\b(?P<attrs>[^>]*)>(?P<body>.*?)</page>", re.DOTALL)
XML_ATTR_RE = re.compile(r'(\w+)="([^"]*)"')
QUALITY_FLAGS_RE = re.compile(r"<quality_flags>(.*?)</quality_flags>", re.DOTALL)
CONTENT_RE = re.compile(r"<content><!\[CDATA\[(.*?)\]\]></content>", re.DOTALL)


def parse_normalized_document_pages(normalized_xml_path: Path) -> list[dict[str, object]]:
    """Parse page payloads from canonical normalized document XML."""
    xml_text = normalized_xml_path.read_text(encoding="utf-8")
    page_records: list[dict[str, object]] = []
    for match in PAGE_BLOCK_RE.finditer(xml_text):
        attrs = {key: html.unescape(value) for key, value in XML_ATTR_RE.findall(match.group("attrs"))}
        body = match.group("body")
        quality_flags_match = QUALITY_FLAGS_RE.search(body)
        quality_flags_text = html.unescape(quality_flags_match.group(1).strip()) if quality_flags_match else ""
        content_match = CONTENT_RE.search(body)
        content = content_match.group(1).replace("]]]]><![CDATA[>", "]]>").strip() if content_match else ""
        page_records.append(
            {
                "page_number": int(attrs.get("number", "0") or "0"),
                "representation": attrs.get("representation") or "missing",
                "source_path": attrs.get("source_path") or None,
                "quality_flags": [flag for flag in quality_flags_text.split(",") if flag],
                "content": content,
            }
        )
    return page_records
