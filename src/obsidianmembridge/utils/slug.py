"""Slug helpers."""

import re


def slugify(text: str) -> str:
    """Return a filesystem-friendly slug for a memory title."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80] or "untitled"
