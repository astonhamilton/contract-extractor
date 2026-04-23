from __future__ import annotations

from packages.llm.shared.agent_runtime.models import HostedToolDefinition


def openai_web_search_preview(
    *,
    search_context_size: str = "medium",
    enabled: bool = True,
) -> HostedToolDefinition:
    """Return the canonical OpenAI web-search hosted tool definition."""
    return HostedToolDefinition(
        name="web_search_preview",
        provider="openai",
        config={"search_context_size": search_context_size},
        enabled=enabled,
    )


def openai_image_generation(
    *,
    size: str | None = None,
    quality: str | None = None,
    background: str | None = None,
    output_format: str | None = None,
    compression: int | None = None,
    partial_images: int | None = None,
    action: str | None = None,
    enabled: bool = True,
) -> HostedToolDefinition:
    """Return the canonical OpenAI image-generation hosted tool definition."""
    config: dict[str, object] = {}
    if size is not None:
        config["size"] = size
    if quality is not None:
        config["quality"] = quality
    if background is not None:
        config["background"] = background
    if output_format is not None:
        config["format"] = output_format
    if compression is not None:
        config["compression"] = compression
    if partial_images is not None:
        config["partial_images"] = partial_images
    if action is not None:
        config["action"] = action
    return HostedToolDefinition(
        name="image_generation",
        provider="openai",
        config=config,
        enabled=enabled,
    )


__all__ = ["openai_image_generation", "openai_web_search_preview"]
