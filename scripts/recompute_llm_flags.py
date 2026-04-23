from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.recompute_llm_flags import (
    build_recompute_llm_flags_report,
    recompute_all_manifest_llm_flags,
    write_recompute_llm_flags_report,
)


def main() -> None:
    """Recompute split LLM recommendation flags from current manifest page state."""
    configure_logging()
    print("Starting manifest LLM flag recompute.")
    print("This is a metadata cleanup pass. It does not rerun OCR or any LLM calls.")
    print("It rewrites page/doc LLM recommendation flags from current selector logic.")

    manifests = recompute_all_manifest_llm_flags(REPO_ROOT / "data" / "processed" / "contracts")
    report = build_recompute_llm_flags_report(manifests)
    report_path = REPO_ROOT / "data" / "processed" / "indexes" / "recompute_llm_flags_report.json"
    write_recompute_llm_flags_report(report_path, report)

    print(
        "LLM flag recompute complete: "
        f"docs={report['total_documents']} | "
        f"markdown_docs={report['llm_markdown_recommended_documents']} | "
        f"repair_docs={report['llm_repair_recommended_documents']} | "
        f"legacy_docs={report['legacy_llm_normalization_recommended_documents']}"
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
