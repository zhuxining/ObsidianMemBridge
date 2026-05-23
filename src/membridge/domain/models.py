from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

VALID_STATUSES = frozenset({"active", "archived"})


class MemoryFrontmatter(BaseModel):
    status: str = "active"
    type: str
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scope: str | None = None
    project: str | None = None
    tags: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None

    model_config = ConfigDict(extra="allow")


class MemoryDocument(BaseModel):
    path: str
    title: str
    frontmatter: MemoryFrontmatter
    content: str
    summary: str


class MemoryFilter(BaseModel):
    status: str | None = None
    type: str | None = None
    scope: str | None = None
    project: str | None = None
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    fields: dict[str, str | int | bool | list[str]] = Field(default_factory=dict)
