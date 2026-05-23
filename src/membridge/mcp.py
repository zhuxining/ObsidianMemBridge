"""MCP server — FastMCP tools for MemBridge."""

from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP

from .config import Settings
from .domain.models import MemoryFilter, MemoryFrontmatter
from .services.memory import MemoryService

mcp = FastMCP("MemBridge")


def _service() -> MemoryService:
    settings = Settings()
    return MemoryService(settings)


@mcp.tool()
def read_memories(
    path: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    scope: Optional[str] = None,
    project: Optional[str] = None,
    source: Optional[str] = None,
    tags: Optional[list[str]] = None,
    vault_root: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Read a single memory by path, or query memories with filters."""
    svc = _service()
    if vault_root:
        svc.init_vault(Path(vault_root))
    else:
        svc._require_store()

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
    scope: Optional[str] = None,
    project: Optional[str] = None,
    tags: Optional[list[str]] = None,
    path: Optional[str] = None,
    vault_root: Optional[str] = None,
) -> dict[str, Any]:
    """Write a new memory to the vault."""
    svc = _service()
    if vault_root:
        svc.init_vault(Path(vault_root))
    else:
        svc._require_store()

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
    content: Optional[str] = None,
    frontmatter_patch: Optional[dict[str, Any]] = None,
    vault_root: Optional[str] = None,
) -> dict[str, Any]:
    """Update an existing memory."""
    svc = _service()
    if vault_root:
        svc.init_vault(Path(vault_root))
    else:
        svc._require_store()

    doc = svc.update_memory(path, content, frontmatter_patch)
    return doc.model_dump(mode="json")
