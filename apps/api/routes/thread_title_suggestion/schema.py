from __future__ import annotations

from pydantic import Field

from packages.schemas.common import BaseSchema


class ThreadTitleSuggestionRequest(BaseSchema):
    """Request payload for generating a thread title from one message."""

    message: str = Field(min_length=1)


class ThreadTitleSuggestionResponse(BaseSchema):
    """Response payload containing one suggested title."""

    title: str
