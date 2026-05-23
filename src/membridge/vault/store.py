"""Obsidian Vault storage adapter."""

from pathlib import Path
from typing import Any

from ..domain.errors import NotFoundError, ValidationError
from ..domain.models import MemoryDocument, MemoryFilter, MemoryFrontmatter
from ..domain.validation import check_sensitive_keys, validate_frontmatter_required
from .markdown import read_file_markdown, write_file_markdown
from .paths import list_md_files, make_vault_relative, vault_path_guard


class VaultInfo:
    root: Path
    memories_dir: str

    def __init__(self, root: Path, memories_dir: str = "memories"):
        self.root = root
        self.memories_dir = memories_dir

    def __repr__(self) -> str:
        return f"VaultInfo(root={self.root}, dir={self.memories_dir})"


class ObsidianVaultStore:
    """Low-level read/write against an Obsidian vault."""

    def __init__(self, vault_root: Path, memories_dir: str = "memories"):
        self.vault_root = vault_root.resolve()
        self.memories_dir = memories_dir
        # Ensure the memories directory exists
        (self.vault_root / self.memories_dir).mkdir(parents=True, exist_ok=True)

    # -- read -----------------------------------------------------------------

    def read(self, vault_relative_path: str) -> tuple[dict[str, Any], str]:
        """Return ``(frontmatter_dict, body)`` for a vault-relative path."""
        abs_path = vault_path_guard(self.vault_root, vault_relative_path)
        return read_file_markdown(abs_path)

    # -- write ----------------------------------------------------------------

    def write(
        self,
        title: str,
        frontmatter: dict[str, Any],
        body: str,
        vault_relative_path: str | None = None,
    ) -> str:
        """Write a new memory file. Returns the vault-relative path."""
        # Validate frontmatter
        validate_frontmatter_required(frontmatter)

        # Check for sensitive keys
        sensitive = check_sensitive_keys(frontmatter)
        if sensitive:
            raise ValidationError(f"Sensitive keys detected in frontmatter: {', '.join(sensitive)}")

        if vault_relative_path:
            abs_path = vault_path_guard(self.vault_root, vault_relative_path)
            if abs_path.exists():
                raise ValidationError(f"File already exists: {vault_relative_path}")
        else:
            # Auto-generate path under memories_dir
            slug = _slugify(title)
            base = self.vault_root / self.memories_dir / f"{slug}.md"
            abs_path = _unique_path(base)
            vault_relative_path = make_vault_relative(self.vault_root, abs_path)

        write_file_markdown(abs_path, frontmatter, body)
        return vault_relative_path

    # -- update ---------------------------------------------------------------

    def update(
        self,
        vault_relative_path: str,
        frontmatter_patch: dict[str, Any] | None = None,
        body: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Patch an existing file. Returns ``(updated_frontmatter, updated_body)``."""
        abs_path = vault_path_guard(self.vault_root, vault_relative_path)
        existing_fm, existing_body = read_file_markdown(abs_path)

        new_fm = {**existing_fm, **(frontmatter_patch or {})}
        new_body = body if body is not None else existing_body

        validate_frontmatter_required(new_fm)
        sensitive = check_sensitive_keys(new_fm)
        if sensitive:
            raise ValidationError(f"Sensitive keys detected: {', '.join(sensitive)}")

        write_file_markdown(abs_path, new_fm, new_body)
        return new_fm, new_body

    # -- query ----------------------------------------------------------------

    def query(self, filters: MemoryFilter) -> list[tuple[str, dict[str, Any], str]]:
        """Scan ``.md`` files and return matches as ``(vault_rel_path, fm, body)``."""
        results: list[tuple[str, dict[str, Any], str]] = []
        warnings: list[str] = []

        for md_file in list_md_files(self.vault_root):
            rel = make_vault_relative(self.vault_root, md_file)
            try:
                fm, body = read_file_markdown(md_file)
            except (NotFoundError, ValidationError) as exc:
                warnings.append(f"Skipping {rel}: {exc}")
                continue

            if not fm.keys() & {"status", "type", "source"}:
                # Not a MemBridge memory file
                continue

            if not _matches(fm, filters):
                continue

            results.append((rel, fm, body))

        # Sort: updated_at desc, created_at desc, path asc
        from datetime import datetime, timezone

        def sort_key(item: tuple) -> tuple:
            _, fm, _ = item
            updated = fm.get("updated_at") or datetime.max.replace(tzinfo=timezone.utc)
            created = fm.get("created_at") or datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(updated, str):
                updated = datetime.fromisoformat(updated)
            if isinstance(created, str):
                created = datetime.fromisoformat(created)
            return (-updated.timestamp(), -created.timestamp(), item[0])

        results.sort(key=sort_key)
        return results


# -- helpers ------------------------------------------------------------------

def _slugify(text: str) -> str:
    import re
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:80] or "untitled"


def _unique_path(base: Path) -> Path:
    if not base.exists():
        return base
    i = 1
    while (base.parent / f"{base.stem}-{i}{base.suffix}").exists():
        i += 1
    return base.parent / f"{base.stem}-{i}{base.suffix}"


def _matches(fm: dict[str, Any], f: MemoryFilter) -> bool:
    """Check if a frontmatter dict matches a ``MemoryFilter``."""
    if f.status and fm.get("status") != f.status:
        return False
    if f.type and fm.get("type") != f.type:
        return False
    if f.scope and fm.get("scope") != f.scope:
        return False
    if f.project and fm.get("project") != f.project:
        return False
    if f.source and fm.get("source") != f.source:
        return False
    if f.tags:
        doc_tags = set(fm.get("tags", []))
        if not set(f.tags).issubset(doc_tags):
            return False
    for key, val in f.fields.items():
        if fm.get(key) != val:
            return False
    return True
