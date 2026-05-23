"""Application service — the single entry point for all memory operations."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import Settings
from ..domain.errors import NotFoundError, ValidationError
from ..domain.models import MemoryDocument, MemoryFilter, MemoryFrontmatter
from ..domain.validation import validate_frontmatter_required
from ..vault.store import ObsidianVaultStore, VaultInfo


class MemoryService:
    """High-level API that CLI and MCP both use."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or Settings()
        self._store: ObsidianVaultStore | None = None

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
        self._store = ObsidianVaultStore(root, self._settings.memories_dir)
        return VaultInfo(root, self._settings.memories_dir)

    def _require_store(self) -> ObsidianVaultStore:
        if self._store is None:
            raise ValidationError("Vault not initialized. Call init_vault() or run `meb init`.")
        return self._store

    # -- read -----------------------------------------------------------------

    def read_memory(self, path: str) -> MemoryDocument:
        store = self._require_store()
        fm, body = store.read(path)
        validate_frontmatter_required(fm)
        frontmatter = MemoryFrontmatter(**fm)
        return MemoryDocument(
            path=path,
            title=body.split("\n")[0].lstrip("# ").strip() or frontmatter.type,
            frontmatter=frontmatter,
            content=body,
            summary=_summarize(body, self._settings.summary_chars),
        )

    # -- query ----------------------------------------------------------------

    def query_memories(self, filters: MemoryFilter | None = None) -> list[MemoryDocument]:
        store = self._require_store()
        f = filters or MemoryFilter()
        raw = store.query(f)
        docs: list[MemoryDocument] = []
        for rel_path, fm, body in raw:
            validate_frontmatter_required(fm)
            frontmatter = MemoryFrontmatter(**fm)
            docs.append(
                MemoryDocument(
                    path=rel_path,
                    title=body.split("\n")[0].lstrip("# ").strip() or frontmatter.type,
                    frontmatter=frontmatter,
                    content=body,
                    summary=_summarize(body, self._settings.summary_chars),
                )
            )
        return docs

    # -- write ----------------------------------------------------------------

    def write_memory(
        self,
        title: str,
        content: str,
        frontmatter: MemoryFrontmatter,
        path: str | None = None,
    ) -> MemoryDocument:
        store = self._require_store()
        fm_dict = frontmatter.model_dump(mode="python", exclude_unset=False)
        # Remove None values so YAML stays clean
        fm_dict = {k: v for k, v in fm_dict.items() if v is not None}
        validate_frontmatter_required(fm_dict)

        # Auto-generate updated_at on write is not needed (it's a new file)
        body = f"# {title}\n\n{content}"
        rel_path = store.write(title, fm_dict, body, path)

        return MemoryDocument(
            path=rel_path,
            title=title,
            frontmatter=frontmatter,
            content=content,
            summary=_summarize(content, self._settings.summary_chars),
        )

    # -- update ---------------------------------------------------------------

    def update_memory(
        self,
        path: str,
        content: str | None = None,
        frontmatter_patch: dict[str, Any] | None = None,
    ) -> MemoryDocument:
        store = self._require_store()

        # Auto-set updated_at
        patch = dict(frontmatter_patch or {})
        patch["updated_at"] = datetime.now(timezone.utc)

        new_fm, new_body = store.update(path, patch, content)
        validate_frontmatter_required(new_fm)
        frontmatter = MemoryFrontmatter(**new_fm)

        return MemoryDocument(
            path=path,
            title=new_body.split("\n")[0].lstrip("# ").strip() or frontmatter.type,
            frontmatter=frontmatter,
            content=new_body,
            summary=_summarize(new_body, self._settings.summary_chars),
        )


def _summarize(text: str, max_chars: int) -> str:
    """Truncate text to *max_chars*, preserving whole words."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cutoff = text[:max_chars].rfind(" ")
    if cutoff < max_chars // 2:
        cutoff = max_chars
    return text[:cutoff] + "…"
