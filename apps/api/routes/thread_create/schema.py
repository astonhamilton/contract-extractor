from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from packages.schemas.common import BaseSchema


class ThreadCreateItemRequest(BaseSchema):
    """One initial item posted at thread creation time."""

    type: Literal["text"]
    data: str = Field(min_length=1)


class ThreadCreateRequest(BaseSchema):
    """Request payload for creating one thread."""

    title: str | None = None
    items: list[ThreadCreateItemRequest] = Field(default_factory=list, max_length=1)

    @model_validator(mode="after")
    def validate_non_empty_create_request(self) -> "ThreadCreateRequest":
        """Require a title or one initial text item when creating a thread."""
        has_title = bool(self.title and self.title.strip())
        has_text_item = any(item.data.strip() for item in self.items)
        if not has_title and not has_text_item:
            raise ValueError("Provide either a title or one initial text item.")
        return self


class ThreadCreateThreadResponse(BaseSchema):
    """Created thread shell returned to the client."""

    thread_id: str
    thread_kind: str
    agent_id: str
    title: str
    created_at: str
    updated_at: str
    status: str
    phase: str
    active_turn_id: str | None = None
    last_turn_id: str | None = None
    execution_options: dict[str, object]
    metadata: dict[str, object]


class ThreadCreateTurnResponse(BaseSchema):
    """Optional enqueued-turn summary created with the thread."""

    turn_id: str
    status: str
    phase: str


class ThreadCreateResponse(BaseSchema):
    """Response payload for one created thread."""

    thread: ThreadCreateThreadResponse
    turn: ThreadCreateTurnResponse | None = None
