"""Cross-cutting security: sensitive content detection."""

import re

_SENSITIVE_PATTERNS = [
    re.compile(r"(?:api[_-]?key|secret[_-]?key|password|auth[_-]?token|private[_-]?key)", re.I),
    re.compile(r"(?:sk-[A-Za-z0-9]{20,})"),  # OpenAI-style keys
    re.compile(r"(?:ghp_[A-Za-z0-9]{36})"),   # GitHub PAT
]


def is_sensitive_content(text: str) -> list[str]:
    """Return a list of matched sensitive patterns found in *text*."""
    return [p.pattern for p in _SENSITIVE_PATTERNS if p.search(text)]
