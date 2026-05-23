"""Unit tests for vault path guards."""

from pathlib import Path

import pytest

from membridge.domain.errors import ValidationError
from membridge.vault.paths import make_vault_relative, vault_path_guard


class TestVaultPathGuard:
    def test_valid_relative_path(self, tmp_path: Path):
        vault = tmp_path
        (vault / "memories").mkdir()
        result = vault_path_guard(vault, "memories/test.md")
        assert result == vault / "memories" / "test.md"

    def test_rejects_absolute_path(self, tmp_path: Path):
        vault = tmp_path
        (vault / "memories").mkdir()
        with pytest.raises(ValidationError, match="absolute"):
            vault_path_guard(vault, "/etc/passwd.md")

    def test_rejects_non_md(self, tmp_path: Path):
        vault = tmp_path
        (vault / "memories").mkdir()
        with pytest.raises(ValidationError, match="Only .md"):
            vault_path_guard(vault, "notes/test.txt")

    def test_rejects_path_escape(self, tmp_path: Path):
        vault = tmp_path
        (vault / "memories").mkdir()
        with pytest.raises(ValidationError, match="escapes"):
            vault_path_guard(vault, "../../etc/passwd.md")

    def test_accepts_nested_path(self, tmp_path: Path):
        vault = tmp_path
        (vault / "memories" / "sub").mkdir(parents=True)
        result = vault_path_guard(vault, "memories/sub/deep.md")
        assert "deep.md" in str(result)


class TestMakeVaultRelative:
    def test_basic(self, tmp_path: Path):
        vault = tmp_path
        (vault / "memories").mkdir()
        abs_p = vault / "memories" / "foo.md"
        assert make_vault_relative(vault, abs_p) == "memories/foo.md"
