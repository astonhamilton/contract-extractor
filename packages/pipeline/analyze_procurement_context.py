from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from packages.schemas import DocumentManifest, ProcurementContext


def load_manifests_with_procurement_context(processed_contracts_dir: Path) -> list[DocumentManifest]:
    """Load manifests that already have canonical procurement-context output."""
    manifests: list[DocumentManifest] = []
    if not processed_contracts_dir.exists():
        return manifests

    for doc_dir in sorted(processed_contracts_dir.iterdir()):
        if not doc_dir.is_dir():
            continue
        manifest_path = doc_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = DocumentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        if manifest.procurement_context_path:
            manifests.append(manifest)
    return manifests


def load_procurement_context(repo_root: Path, manifest: DocumentManifest) -> ProcurementContext:
    """Load canonical procurement-context JSON for one manifest."""
    if not manifest.procurement_context_path:
        raise FileNotFoundError(f"Manifest missing procurement_context_path: {manifest.doc_id}")
    context_path = repo_root / manifest.procurement_context_path
    return ProcurementContext.model_validate_json(context_path.read_text(encoding="utf-8"))


def normalize_bucket_value(value: str | None) -> str:
    """Normalize null-ish values into one printable bucket label."""
    if value is None:
        return "(null)"
    stripped = value.strip()
    return stripped if stripped else "(blank)"


def top_counter_items(counter: Counter[str], limit: int = 20) -> list[dict[str, object]]:
    """Convert a counter into a sorted JSON-friendly top-N list."""
    items = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [{"name": name, "count": count} for name, count in items[:limit]]


def build_procurement_context_report(
    repo_root: Path,
    manifests: list[DocumentManifest],
) -> dict[str, object]:
    """Build a grouping/bucketing report over canonical procurement-context outputs."""
    total_docs = len(manifests)
    procurement_gate_counts: Counter[str] = Counter()
    buyer_counts: Counter[str] = Counter()
    seller_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    buyer_seller_pair_counts: Counter[str] = Counter()
    category_by_buyer: dict[str, Counter[str]] = defaultdict(Counter)
    seller_by_category: dict[str, Counter[str]] = defaultdict(Counter)
    missing_field_counts: Counter[str] = Counter()
    examples_by_category: dict[str, list[dict[str, object]]] = defaultdict(list)
    examples_by_buyer: dict[str, list[dict[str, object]]] = defaultdict(list)

    for manifest in manifests:
        context = load_procurement_context(repo_root, manifest)
        gate_value = context.is_procurement_doc.value
        buyer_value = normalize_bucket_value(context.buyer)
        seller_value = normalize_bucket_value(context.seller)
        category_value = normalize_bucket_value(
            context.procurement_category.value if context.procurement_category is not None else None
        )
        pair_value = f"{buyer_value} -> {seller_value}"

        procurement_gate_counts[gate_value] += 1
        buyer_counts[buyer_value] += 1
        seller_counts[seller_value] += 1
        category_counts[category_value] += 1
        buyer_seller_pair_counts[pair_value] += 1
        category_by_buyer[buyer_value][category_value] += 1
        seller_by_category[category_value][seller_value] += 1

        if context.buyer is None:
            missing_field_counts["buyer"] += 1
        if context.seller is None:
            missing_field_counts["seller"] += 1
        if context.procurement_subject_summary is None:
            missing_field_counts["procurement_subject_summary"] += 1
        if context.procurement_category is None:
            missing_field_counts["procurement_category"] += 1

        example = {
            "doc_id": manifest.doc_id,
            "source_filename": manifest.source_filename,
            "buyer": context.buyer,
            "seller": context.seller,
            "procurement_subject_summary": context.procurement_subject_summary,
            "confidence": context.confidence,
            "procurement_context_path": manifest.procurement_context_path,
        }
        if len(examples_by_category[category_value]) < 5:
            examples_by_category[category_value].append(example)
        if len(examples_by_buyer[buyer_value]) < 5:
            examples_by_buyer[buyer_value].append(example)

    buyers_section = []
    for buyer_name, buyer_counter in sorted(buyer_counts.items(), key=lambda item: (-item[1], item[0]))[:20]:
        buyers_section.append(
            {
                "buyer": buyer_name,
                "count": buyer_counts[buyer_name],
                "top_categories": top_counter_items(category_by_buyer[buyer_name], limit=10),
                "examples": examples_by_buyer[buyer_name],
            }
        )

    categories_section = []
    for category_name, _ in sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))[:20]:
        categories_section.append(
            {
                "category": category_name,
                "count": category_counts[category_name],
                "top_sellers": top_counter_items(seller_by_category[category_name], limit=10),
                "examples": examples_by_category[category_name],
            }
        )

    return {
        "total_documents": total_docs,
        "documents_with_procurement_context": total_docs,
        "gate_counts": dict(sorted(procurement_gate_counts.items())),
        "missing_field_counts": dict(sorted(missing_field_counts.items())),
        "top_buyers": buyers_section,
        "top_sellers": top_counter_items(seller_counts, limit=25),
        "top_categories": categories_section,
        "top_buyer_seller_pairs": top_counter_items(buyer_seller_pair_counts, limit=25),
    }


def write_procurement_context_report(report_path: Path, report: dict[str, object]) -> None:
    """Write the procurement-context analysis report to disk."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def report_summary_line(report: dict[str, object]) -> str:
    """Return a compact one-line summary for terminal output."""
    gate_counts = report.get("gate_counts", {})
    formatted_gates = ", ".join(f"{name}={count}" for name, count in sorted(gate_counts.items()))
    return (
        f"docs={report['total_documents']} | "
        f"gate={formatted_gates or '-'} | "
        f"buyers={len(report['top_buyers'])} | "
        f"categories={len(report['top_categories'])}"
    )
