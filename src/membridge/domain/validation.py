import re

from .errors import ValidationError
from .models import VALID_STATUSES

REQUIRED_FRONTMATTER_KEYS = {"status", "type", "source", "created_at"}

SENSITIVE_PATTERNS = [
    re.compile(r"(?:api_?key|secret|password|token|private_?key)", re.IGNORECASE),
]


def validate_frontmatter_required(data: dict[str, object]) -> None:
    """Check that all required frontmatter keys are present and valid."""
    missing = REQUIRED_FRONTMATTER_KEYS - data.keys()
    if missing:
        raise ValidationError(f"Missing required frontmatter keys: {', '.join(sorted(missing))}")

    status = data.get("status")
    if status not in VALID_STATUSES:
        raise ValidationError(
            f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )


def check_sensitive_keys(data: dict[str, object], path: str = "") -> list[str]:
    """Return a list of keys that look like secrets."""
    found: list[str] = []
    for key, value in data.items():
        if any(p.search(key) for p in SENSITIVE_PATTERNS):
            found.append(f"{path}.{key}" if path else key)
    return found
