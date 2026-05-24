"""MemBridge — Obsidian-based shared memory layer for agents."""

from .core import MemoryService, VaultInfo
from .settings import Settings

__all__ = ["MemoryService", "Settings", "VaultInfo"]
