from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class BaseSchema(BaseModel):
    model_config = {
        "extra": "forbid",
        "populate_by_name": True,
    }


class StageStatus(BaseSchema):
    status: ProcessingStatus = ProcessingStatus.PENDING
    updated_at: datetime = Field(default_factory=utc_now)
    version: str = "0.1.0"
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
