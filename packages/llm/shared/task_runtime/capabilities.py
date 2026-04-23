from __future__ import annotations


SUPPORTED_REASONING_EFFORTS = {"none", "low", "medium", "high", "xhigh"}


def _validate_reasoning_effort(reasoning_effort: str | None) -> None:
    """Fail fast on unsupported reasoning-effort values before API dispatch."""
    if reasoning_effort is None:
        return
    if reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
        supported = ", ".join(sorted(SUPPORTED_REASONING_EFFORTS))
        raise ValueError(
            f"Unsupported reasoning_effort={reasoning_effort!r}. Supported values: {supported}."
        )


def model_supports_reasoning_effort(model: str) -> bool:
    """Return True when the model/provider path should receive reasoning_effort."""
    return model.startswith("openai/")


def model_supports_strict_structured_output(model: str) -> bool:
    """Return True when the model/provider path is approved for strict JSON-schema mode here."""
    return model.startswith("openai/") or model.startswith("anthropic/")


def effective_reasoning_effort(model: str, reasoning_effort: str | None) -> str | None:
    """Return the effective reasoning effort after provider-aware filtering."""
    _validate_reasoning_effort(reasoning_effort)
    if not model_supports_reasoning_effort(model):
        return None
    return reasoning_effort
