"""Core service — unified memory operations with vault storage."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from obsidianmembridge.models import (
    MemoryDocument,
    MemoryFilter,
    MemoryFrontmatter,
    ValidationError,
)
from obsidianmembridge.settings import Settings
from obsidianmembridge.utils.markdown import read_file_markdown, write_file_markdown
from obsidianmembridge.utils.paths import list_md_files, make_vault_relative, vault_path_guard
from obsidianmembridge.utils.slug import slugify
from obsidianmembridge.utils.text import summarize
from obsidianmembridge.utils.validation import check_sensitive_keys, validate_frontmatter_required


class VaultInfo:
    """Information about a initialized vault."""

    root: Path
    memories_dir: str

    def __init__(self, root: Path, memories_dir: str = "memories"):
        self.root = root
        self.memories_dir = memories_dir

    def __repr__(self) -> str:
        return f"VaultInfo(root={self.root}, dir={self.memories_dir})"


class MemoryService:
    """Unified service for all memory operations."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or Settings()
        self._vault_root: Path | None = None

    # -- vault lifecycle ------------------------------------------------------

    def init_vault(self, vault_root: Path | None = None) -> VaultInfo:
        """Initialize (or re-point) the vault."""
        root = vault_root or self._settings.vault_root
        if not root:
            raise ValidationError(
                "No vault_root provided. Pass --vault-root, set MEMBRIDGE_VAULT_ROOT, "
                "or call init_vault(vault_root=...)."
            )
        root = root.resolve()
        if not root.is_dir():
            raise ValidationError(f"Vault root does not exist: {root}")

        self._vault_root = root
        memories_path = root / self._settings.memories_dir
        memories_path.mkdir(parents=True, exist_ok=True)
        return VaultInfo(root, self._settings.memories_dir)

    def _require_vault(self) -> Path:
        if self._vault_root is None:
            raise ValidationError("Vault not initialized. Call init_vault() or run `meb init`.")
        return self._vault_root

    # -- read -----------------------------------------------------------------

    def read_memory(self, path: str) -> MemoryDocument:
        vault = self._require_vault()
        abs_path = vault_path_guard(vault, path)
        fm, body = read_file_markdown(abs_path)
        validate_frontmatter_required(fm)
        frontmatter = MemoryFrontmatter(**fm)
        return MemoryDocument(
            path=path,
            title=body.split("\n")[0].lstrip("# ").strip() or frontmatter.type,
            frontmatter=frontmatter,
            content=body,
            summary=summarize(body, self._settings.summary_chars),
        )

    # -- query ----------------------------------------------------------------

    def query_memories(self, filters: MemoryFilter | None = None) -> list[MemoryDocument]:
        vault = self._require_vault()
        f = filters or MemoryFilter()
        docs: list[MemoryDocument] = []

        for md_file in list_md_files(vault):
            rel = make_vault_relative(vault, md_file)
            try:
                fm, body = read_file_markdown(md_file)
            except ValidationError:
                continue

            if not fm.keys() & {"status", "type", "source"}:
                continue

            if not _matches(fm, f):
                continue

            try:
                validate_frontmatter_required(fm)
                frontmatter = MemoryFrontmatter(**fm)
                docs.append(
                    MemoryDocument(
                        path=rel,
                        title=body.split("\n")[0].lstrip("# ").strip() or frontmatter.type,
                        frontmatter=frontmatter,
                        content=body,
                        summary=summarize(body, self._settings.summary_chars),
                    )
                )
            except ValidationError:
                continue

        # Sort: updated_at desc, created_at desc, path asc
        docs.sort(key=_sort_key)
        return docs

    # -- write ----------------------------------------------------------------

    def write_memory(
        self,
        title: str,
        content: str,
        frontmatter: MemoryFrontmatter,
        path: str | None = None,
    ) -> MemoryDocument:
        vault = self._require_vault()

        fm_dict = frontmatter.model_dump(mode="python", exclude_unset=False)
        fm_dict = {k: v for k, v in fm_dict.items() if v is not None}
        validate_frontmatter_required(fm_dict)

        sensitive = check_sensitive_keys(fm_dict)
        if sensitive:
            raise ValidationError(f"Sensitive keys detected: {', '.join(sensitive)}")

        body = f"# {title}\n\n{content}"

        if path:
            abs_path = vault_path_guard(vault, path)
            if abs_path.exists():
                raise ValidationError(f"File already exists: {path}")
            rel_path = path
        else:
            slug = slugify(title)
            base = vault / self._settings.memories_dir / f"{slug}.md"
            abs_path = _unique_path(base)
            rel_path = make_vault_relative(vault, abs_path)

        write_file_markdown(abs_path, fm_dict, body)

        return MemoryDocument(
            path=rel_path,
            title=title,
            frontmatter=frontmatter,
            content=content,
            summary=summarize(content, self._settings.summary_chars),
        )

    # -- update ---------------------------------------------------------------

    def update_memory(
        self,
        path: str,
        content: str | None = None,
        frontmatter_patch: dict[str, Any] | None = None,
    ) -> MemoryDocument:
        vault = self._require_vault()
        abs_path = vault_path_guard(vault, path)

        existing_fm, existing_body = read_file_markdown(abs_path)

        new_fm = {**existing_fm, **(frontmatter_patch or {})}
        new_fm["updated_at"] = datetime.now(UTC)
        new_body = content if content is not None else existing_body

        validate_frontmatter_required(new_fm)
        sensitive = check_sensitive_keys(new_fm)
        if sensitive:
            raise ValidationError(f"Sensitive keys detected: {', '.join(sensitive)}")

        write_file_markdown(abs_path, new_fm, new_body)

        frontmatter = MemoryFrontmatter(**new_fm)
        return MemoryDocument(
            path=path,
            title=new_body.split("\n")[0].lstrip("# ").strip() or frontmatter.type,
            frontmatter=frontmatter,
            content=new_body,
            summary=summarize(new_body, self._settings.summary_chars),
        )


# -- private helpers -----------------------------------------------------------


def _matches(fm: dict[str, Any], f: MemoryFilter) -> bool:
    """Check if frontmatter matches the filter."""
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
    return all(fm.get(key) == val for key, val in f.fields.items())


def _sort_key(doc: MemoryDocument) -> tuple:
    """Sort by updated_at desc, created_at desc, path asc."""
    updated = doc.frontmatter.updated_at or datetime.max.replace(tzinfo=UTC)
    created = doc.frontmatter.created_at
    return (-updated.timestamp(), -created.timestamp(), doc.path)


def _unique_path(base: Path) -> Path:
    """Generate a unique path if file exists."""
    if not base.exists():
        return base
    i = 1
    while (base.parent / f"{base.stem}-{i}{base.suffix}").exists():
        i += 1
    return base.parent / f"{base.stem}-{i}{base.suffix}"
