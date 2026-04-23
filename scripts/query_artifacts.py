from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.pipeline.logging_utils import configure_logging
from packages.pipeline.normalize.query_artifacts import run_artifact_query


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for flat artifact query exports."""
    parser = argparse.ArgumentParser(description="Query candidate artifacts and dump flat symlink exports into a chosen folder.")
    parser.add_argument(
        "--selector",
        required=True,
        choices=("markdown", "repair", "skipped_repair", "markdown_generated", "repaired", "failed"),
        help="Candidate selector to apply.",
    )
    parser.add_argument(
        "--artifacts",
        required=True,
        help="Comma-separated artifact names to export: pdf,image,ocr_text,text,manifest,markdown,repair_markdown.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Repo-relative or absolute output folder. Artifacts are linked flatly into this folder.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional deterministic sample size.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed used with --limit.")
    return parser.parse_args()


def resolve_output_dir(raw_output_dir: str) -> Path:
    """Resolve an output directory argument relative to the repo root when needed."""
    path = Path(raw_output_dir)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def main() -> None:
    """Run a flat artifact query export into a user-chosen sampled folder."""
    configure_logging()
    args = parse_args()
    artifact_names = [artifact.strip() for artifact in args.artifacts.split(",") if artifact.strip()]
    output_dir = resolve_output_dir(args.output_dir)

    print("Starting flat artifact query export.")
    print("This creates symlinks in one chosen folder rather than a timestamped sampling tree.")
    print(
        f"Selector={args.selector} | artifacts={','.join(artifact_names)} | "
        f"limit={args.limit if args.limit is not None else 'all'} | seed={args.seed}"
    )

    report = run_artifact_query(
        repo_root=REPO_ROOT,
        selector_name=args.selector,
        artifact_names=artifact_names,
        output_dir=output_dir,
        limit=args.limit,
        seed=args.seed,
    )

    print(
        "Artifact query complete: "
        f"count={report['count']} | output_dir={output_dir}"
    )
    print(f"Report written to {output_dir / 'query_report.json'}")


if __name__ == "__main__":
    main()
