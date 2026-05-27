"""Parse and serialize Markdown files with YAML frontmatter."""

import re
from typing import Any

import yaml

from obsidianmembridge.models import NotFoundError, ValidationError

FRONTMATTER_RE = re.compile(r"^---\n(?:([^\n].*?)\n)?---\n", re.DOTALL)


def parse_markdown(text: str) -> tuple[dict[str, Any], str]:
    """Split Markdown text into ``(frontmatter_dict, body)``.

    If no frontmatter block is found, returns ``({}, text)``.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1) or "") or {}
    body = text[m.end() :]
    return fm, body


def serialize_markdown(frontmatter: dict[str, Any], body: str) -> str:
    """Combine a frontmatter dict and body into a Markdown string."""
    fm_text = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_text}---\n{body}"


def read_file_markdown(path) -> tuple[dict[str, Any], str]:
    """Read a file and parse its frontmatter.

    Raises ``NotFoundError`` if the file doesn't exist.
    Raises ``ValidationError`` if YAML is malformed.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise NotFoundError(f"File not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ValidationError(f"File is not valid UTF-8: {path}") from exc

    try:
        return parse_markdown(text)
    except yaml.YAMLError as exc:
        raise ValidationError(f"Invalid YAML frontmatter in {path}: {exc}") from exc


def write_file_markdown(path, frontmatter: dict[str, Any], body: str) -> None:
    """Serialize and write Markdown with frontmatter to *path*."""
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    content = serialize_markdown(frontmatter, body)
    path.write_text(content, encoding="utf-8")
