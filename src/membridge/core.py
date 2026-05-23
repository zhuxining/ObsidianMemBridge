"""Core logic for MemBridge."""

from dataclasses import dataclass


@dataclass
class Bridge:
    source: str
    target: str = "memory"

    def describe(self) -> str:
        return f"MemBridge: {self.source} -> {self.target}"


def create_bridge(source: str, target: str = "memory") -> Bridge:
    cleaned_source = source.strip()
    cleaned_target = target.strip() or "memory"

    if not cleaned_source:
        raise ValueError("source cannot be empty")

    return Bridge(source=cleaned_source, target=cleaned_target)
