"""MemBridge — Obsidian-based shared memory layer for agents."""

from .config import Settings
from .services.memory import MemoryService

__all__ = ["MemoryService", "Settings"]
