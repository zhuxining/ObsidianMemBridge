"""MCP server — FastMCP tools for MemBridge."""

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from membridge.core import MemoryService
from membridge.models import MemoryFilter, MemoryFrontmatter
from membridge.settings import Settings

mcp = FastMCP("MemBridge")


def _service() -> MemoryService:
    settings = Settings()
    return MemoryService(settings)


@mcp.tool()
def read_memories(
    path: str | None = None,
    status: str | None = None,
    type: str | None = None,
    scope: str | None = None,
    project: str | None = None,
    source: str | None = None,
    tags: list[str] | None = None,
    vault_root: str | None = None,
) -> list[dict[str, Any]]:
    """Read a single memory by path, or query memories with filters."""
    svc = _service()
    if vault_root:
        svc.init_vault(Path(vault_root))
    else:
        svc._require_vault()

    if path:
        doc = svc.read_memory(path)
        return [doc.model_dump(mode="json")]

    filters = MemoryFilter(
        status=status,
        type=type,
        scope=scope,
        project=project,
        source=source,
        tags=tags or [],
    )
    docs = svc.query_memories(filters)
    return [d.model_dump(mode="json") for d in docs]


@mcp.tool()
def write_memory(
    title: str,
    content: str,
    type: str,
    source: str,
    status: str = "active",
    scope: str | None = None,
    project: str | None = None,
    tags: list[str] | None = None,
    path: str | None = None,
    vault_root: str | None = None,
) -> dict[str, Any]:
    """Write a new memory to the vault."""
    svc = _service()
    if vault_root:
        svc.init_vault(Path(vault_root))
    else:
        svc._require_vault()

    frontmatter = MemoryFrontmatter(
        status=status,
        type=type,
        source=source,
        scope=scope,
        project=project,
        tags=tags or [],
    )
    doc = svc.write_memory(title, content, frontmatter, path)
    return doc.model_dump(mode="json")


@mcp.tool()
def update_memory(
    path: str,
    content: str | None = None,
    frontmatter_patch: dict[str, Any] | None = None,
    vault_root: str | None = None,
) -> dict[str, Any]:
    """Update an existing memory."""
    svc = _service()
    if vault_root:
        svc.init_vault(Path(vault_root))
    else:
        svc._require_vault()

    doc = svc.update_memory(path, content, frontmatter_patch)
    return doc.model_dump(mode="json")
