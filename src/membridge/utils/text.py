"""Text helpers."""


def summarize(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, preserving whole words when practical."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cutoff = text[:max_chars].rfind(" ")
    if cutoff < max_chars // 2:
        cutoff = max_chars
    return text[:cutoff] + "…"
