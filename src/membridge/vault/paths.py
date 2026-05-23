"""Vault path security guards."""

from pathlib import Path

from ..domain.errors import ValidationError


def vault_path_guard(vault_root: Path, path: str | Path) -> Path:
    """Validate and return an absolute path inside the vault.

    Raises ``ValidationError`` for:
    - Absolute paths (must be vault-relative)
    - Non-``.md`` files
    - Paths escaping the vault root (``..`` or symlinks)
    """
    p = Path(path) if isinstance(path, str) else path

    if p.is_absolute():
        raise ValidationError(f"Path must be vault-relative, got absolute: {p}")

    if p.suffix != ".md":
        raise ValidationError(f"Only .md files are allowed, got: {p}")

    resolved = (vault_root / p).resolve()
    vault_resolved = vault_root.resolve()

    if not str(resolved).startswith(str(vault_resolved)):
        raise ValidationError(f"Path escapes vault root: {p}")

    return resolved


def make_vault_relative(vault_root: Path, absolute: Path) -> str:
    """Return the vault-relative POSIX path string."""
    return str(absolute.resolve().relative_to(vault_root.resolve()))


def list_md_files(vault_root: Path, directory: str | None = None) -> list[Path]:
    """Recursively find all ``.md`` files under *vault_root* (optionally scoped)."""
    base = vault_root / directory if directory else vault_root
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*.md") if p.is_file())
