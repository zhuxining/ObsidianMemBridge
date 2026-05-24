"""Configuration for MemBridge."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    vault_root: Path | None = None
    memories_dir: str = "memories"
    summary_chars: int = 200

    model_config = {
        "env_prefix": "MEMBRIDGE_",
        "extra": "ignore",
    }
