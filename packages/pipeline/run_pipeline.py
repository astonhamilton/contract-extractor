from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from packages.llm.transforms.markdown_normalization.config import MarkdownNormalizationConfig
from packages.llm.transforms.repair_normalization.config import RepairNormalizationConfig
from packages.pipeline.ingest.inventory import InventoryPaths, inventory_contracts
from packages.pipeline.normalize.assemble_normalized_document import (
    assemble_all_normalized_documents,
    build_assembled_documents_report,
    write_assembled_documents_report,
)
from packages.pipeline.normalize.image_orientation import (
    build_image_orientation_report,
    normalize_image_orientation_documents,
    write_image_orientation_report,
)
from packages.pipeline.normalize.llm_image_orientation import (
    LLMImageOrientationStageConfig,
    apply_llm_image_orientation_run,
    default_llm_orientation_worker_count,
    execute_llm_image_orientation_run,
)
from packages.pipeline.normalize.llm_markdown import (
    build_llm_markdown_report,
    normalize_llm_markdown_documents,
    write_llm_markdown_report,
)
from packages.pipeline.normalize.llm_repair import (
    build_llm_repair_report,
    normalize_llm_repair_documents,
    write_llm_repair_report,
)
from packages.pipeline.normalize.ocr_pages import (
    build_ocr_report,
    normalize_ocr_documents,
    write_ocr_report,
)
from packages.pipeline.normalize.pdf_pages import (
    build_normalization_report,
    normalize_all_documents,
    write_normalization_report,
)
from packages.pipeline.normalize.pipeline_state import (
    build_pipeline_state_report,
    load_pipeline_manifests,
    write_pipeline_state_report,
)
from packages.pipeline.normalize.recompute_llm_flags import (
    build_recompute_llm_flags_report,
    recompute_all_manifest_llm_flags,
    write_recompute_llm_flags_report,
)
from packages.pipeline.normalize.token_inventory import (
    build_token_inventory_report,
    load_token_inventory_manifests,
    write_token_inventory_report,
)
from packages.pipeline.normalize.vision_markdown import (
    VisionMarkdownStageConfig,
    apply_vision_markdown_run,
    default_vision_markdown_worker_count,
    execute_vision_markdown_run,
)


@dataclass(frozen=True)
class PipelineRunConfig:
    """Configuration for the end-to-end pipeline runner."""

    repo_root: Path
    raw_contracts_dir: Path
    processed_contracts_dir: Path
    indexes_dir: Path
    ocr_mode: str = "parallel"
    ocr_workers: int | None = None
    markdown_model: str = "openai/gpt-5.4-mini"
    repair_model: str = "openai/gpt-5.4-mini"
    enable_llm_image_orientation: bool = False
    llm_image_orientation_model: str = "openai/gpt-5.4-nano"
    llm_image_orientation_reasoning_effort: str | None = "none"
    llm_image_orientation_workers: int | None = None
    enable_vision_markdown: bool = False
    vision_markdown_model: str = "openai/gpt-5.4-nano"
    vision_markdown_workers: int | None = None


def default_e2e_ocr_workers() -> int:
    """Return the default OCR worker count for the end-to-end runner."""
    return max(1, os.cpu_count() or 1)


def emit_stage(callback, stage: str, message: str) -> None:
    """Emit a structured stage update when a callback is provided."""
    if callback is not None:
        callback(stage, message)


def run_full_pipeline(config: PipelineRunConfig, stage_callback=None) -> dict[str, object]:
    """Run the full incremental pipeline from inventory through audit."""
    emit_stage(stage_callback, "inventory", "Starting inventory.")
    inventory_records = inventory_contracts(
        InventoryPaths(
            repo_root=config.repo_root,
            raw_contracts_dir=config.raw_contracts_dir,
            processed_contracts_dir=config.processed_contracts_dir,
            documents_index_path=config.indexes_dir / "documents.jsonl",
        )
    )
    emit_stage(stage_callback, "inventory", f"Inventory complete: {len(inventory_records)} indexed documents.")

    emit_stage(stage_callback, "normalize_txt", "Starting text normalization.")
    txt_manifests = normalize_all_documents(
        repo_root=config.repo_root,
        processed_contracts_dir=config.processed_contracts_dir,
    )
    txt_report = build_normalization_report(txt_manifests)
    write_normalization_report(config.indexes_dir / "normalization_report.json", txt_report)
    emit_stage(
        stage_callback,
        "normalize_txt",
        "Text normalization complete: "
        f"completed={txt_report['completed_documents']} | "
        f"failed={txt_report['failed_documents']} | "
        f"ocr_recommended={txt_report['ocr_recommended_documents']}",
    )

    emit_stage(stage_callback, "validate_image_orientation", "Starting page-image orientation validation.")
    orientation_summary = normalize_image_orientation_documents(
        repo_root=config.repo_root,
        processed_contracts_dir=config.processed_contracts_dir,
    )
    orientation_report = build_image_orientation_report(orientation_summary)
    write_image_orientation_report(config.indexes_dir / "image_orientation_report.json", orientation_report)
    emit_stage(
        stage_callback,
        "validate_image_orientation",
        "Page-image orientation validation complete: "
        f"candidate_documents={orientation_summary['candidate_documents']} | "
        f"processed_pages={orientation_summary['processed_pages']} | "
        f"rotated_pages={orientation_summary['rotated_pages']}",
    )

    llm_orientation_report = None
    if config.enable_llm_image_orientation:
        emit_stage(stage_callback, "validate_llm_image_orientation", "Starting LLM page-image orientation validation.")
        llm_orientation_config = LLMImageOrientationStageConfig(
            repo_root=config.repo_root,
            processed_contracts_dir=config.processed_contracts_dir,
            runs_dir=config.repo_root / "data" / "processed" / "llm_image_orientation_runs",
            indexes_dir=config.indexes_dir,
            model=config.llm_image_orientation_model,
            reasoning_effort=config.llm_image_orientation_reasoning_effort,
            workers=config.llm_image_orientation_workers or default_llm_orientation_worker_count(),
        )
        llm_orientation_report, llm_orientation_report_path = execute_llm_image_orientation_run(config=llm_orientation_config)
        apply_llm_image_orientation_run(
            config=llm_orientation_config,
            run_report_path=llm_orientation_report_path,
        )
        emit_stage(
            stage_callback,
            "validate_llm_image_orientation",
            "LLM page-image orientation validation complete: "
            f"selected_pages={llm_orientation_report['pages_selected']} | "
            f"rotated_pages={llm_orientation_report['rotated_pages']} | "
            f"failed={llm_orientation_report['pages_failed']}",
        )

    emit_stage(stage_callback, "normalize_ocr", "Starting OCR normalization.")
    ocr_manifests = normalize_ocr_documents(
        repo_root=config.repo_root,
        processed_contracts_dir=config.processed_contracts_dir,
        mode=config.ocr_mode,
        workers=config.ocr_workers,
    )
    ocr_report = build_ocr_report(ocr_manifests)
    write_ocr_report(config.indexes_dir / "ocr_report.json", ocr_report)
    emit_stage(
        stage_callback,
        "normalize_ocr",
        "OCR normalization complete: "
        f"candidates={ocr_report['total_candidate_documents']} | "
        f"attempted={ocr_report['ocr_attempted_documents']} | "
        f"llm_recommended={ocr_report['llm_recommended_documents']}",
    )

    emit_stage(stage_callback, "recompute_llm_flags", "Recomputing LLM flags before canonical LLM stages.")
    recomputed_manifests = recompute_all_manifest_llm_flags(config.processed_contracts_dir)
    recompute_report = build_recompute_llm_flags_report(recomputed_manifests)
    write_recompute_llm_flags_report(config.indexes_dir / "recompute_llm_flags_report.json", recompute_report)
    emit_stage(
        stage_callback,
        "recompute_llm_flags",
        "LLM flag recompute complete: "
        f"markdown_docs={recompute_report['llm_markdown_recommended_documents']} | "
        f"repair_docs={recompute_report['llm_repair_recommended_documents']}",
    )

    emit_stage(stage_callback, "normalize_llm_markdown", "Starting canonical markdown normalization.")
    markdown_summary = normalize_llm_markdown_documents(
        repo_root=config.repo_root,
        processed_contracts_dir=config.processed_contracts_dir,
        config=MarkdownNormalizationConfig(model=config.markdown_model),
    )
    markdown_report = build_llm_markdown_report(
        config=MarkdownNormalizationConfig(model=config.markdown_model),
        summary=markdown_summary,
    )
    write_llm_markdown_report(config.indexes_dir / "llm_markdown_report.json", markdown_report)
    emit_stage(
        stage_callback,
        "normalize_llm_markdown",
        "Markdown normalization complete: "
        f"candidate_documents={markdown_summary['candidate_documents']} | "
        f"processed_documents={markdown_summary['processed_documents']} | "
        f"processed_pages={markdown_summary['processed_pages']}",
    )

    vision_markdown_report = None
    if config.enable_vision_markdown:
        emit_stage(stage_callback, "normalize_vision_markdown", "Starting canonical vision markdown normalization.")
        vision_config = VisionMarkdownStageConfig(
            repo_root=config.repo_root,
            processed_contracts_dir=config.processed_contracts_dir,
            runs_dir=config.repo_root / "data" / "processed" / "vision_markdown_runs",
            indexes_dir=config.indexes_dir,
            model=config.vision_markdown_model,
            workers=config.vision_markdown_workers or default_vision_markdown_worker_count(),
        )
        vision_markdown_report, vision_markdown_report_path = execute_vision_markdown_run(config=vision_config)
        apply_vision_markdown_run(
            config=vision_config,
            run_report_path=vision_markdown_report_path,
        )
        emit_stage(
            stage_callback,
            "normalize_vision_markdown",
            "Vision markdown normalization complete: "
            f"selected_pages={vision_markdown_report['pages_selected']} | "
            f"succeeded={vision_markdown_report['pages_succeeded']} | "
            f"failed={vision_markdown_report['pages_failed']}",
        )

    emit_stage(stage_callback, "normalize_llm_repair", "Starting canonical repair normalization.")
    repair_summary = normalize_llm_repair_documents(
        repo_root=config.repo_root,
        processed_contracts_dir=config.processed_contracts_dir,
        config=RepairNormalizationConfig(model=config.repair_model),
    )
    repair_report = build_llm_repair_report(
        config=RepairNormalizationConfig(model=config.repair_model),
        summary=repair_summary,
    )
    write_llm_repair_report(config.indexes_dir / "llm_repair_report.json", repair_report)
    emit_stage(
        stage_callback,
        "normalize_llm_repair",
        "Repair normalization complete: "
        f"candidate_documents={repair_summary['candidate_documents']} | "
        f"processed_documents={repair_summary['processed_documents']} | "
        f"processed_pages={repair_summary['processed_pages']}",
    )

    emit_stage(stage_callback, "recompute_llm_flags", "Recomputing LLM flags after canonical LLM stages.")
    recomputed_manifests = recompute_all_manifest_llm_flags(config.processed_contracts_dir)
    recompute_report = build_recompute_llm_flags_report(recomputed_manifests)
    write_recompute_llm_flags_report(config.indexes_dir / "recompute_llm_flags_report.json", recompute_report)
    emit_stage(
        stage_callback,
        "recompute_llm_flags",
        "Post-LLM flag recompute complete: "
        f"markdown_docs={recompute_report['llm_markdown_recommended_documents']} | "
        f"repair_docs={recompute_report['llm_repair_recommended_documents']}",
    )

    emit_stage(stage_callback, "audit", "Running final pipeline state audit.")
    pipeline_manifests = load_pipeline_manifests(config.processed_contracts_dir)
    pipeline_report = build_pipeline_state_report(pipeline_manifests)
    write_pipeline_state_report(config.indexes_dir / "pipeline_state_report.json", pipeline_report)
    emit_stage(
        stage_callback,
        "audit",
        "Pipeline audit complete: "
        f"states={pipeline_report['state_counts']}",
    )

    emit_stage(stage_callback, "assemble_normalized_documents", "Assembling canonical normalized documents.")
    assembled_manifests = assemble_all_normalized_documents(
        repo_root=config.repo_root,
        processed_contracts_dir=config.processed_contracts_dir,
    )
    assembled_report = build_assembled_documents_report(assembled_manifests)
    write_assembled_documents_report(config.indexes_dir / "assembled_documents_report.json", assembled_report)
    emit_stage(
        stage_callback,
        "assemble_normalized_documents",
        f"Normalized document assembly complete: docs={assembled_report['documents_total']}",
    )

    emit_stage(stage_callback, "token_inventory", "Estimating normalized artifact token usage.")
    token_manifests = load_token_inventory_manifests(config.processed_contracts_dir)
    token_report = build_token_inventory_report(config.repo_root, token_manifests)
    write_token_inventory_report(config.indexes_dir / "token_inventory_report.json", token_report)
    emit_stage(
        stage_callback,
        "token_inventory",
        "Token inventory complete: "
        f"best_available_total_tokens={token_report['corpus']['best_available_total_tokens']} | "
        f"by_type={token_report['corpus']['tokens_by_artifact_type']}",
    )

    return {
        "inventory_count": len(inventory_records),
        "txt_report": txt_report,
        "orientation_report": orientation_report,
        "ocr_report": ocr_report,
        "llm_orientation_report": llm_orientation_report,
        "markdown_report": markdown_report,
        "vision_markdown_report": vision_markdown_report,
        "repair_report": repair_report,
        "pipeline_report": pipeline_report,
        "assembled_report": assembled_report,
        "token_report": token_report,
    }
