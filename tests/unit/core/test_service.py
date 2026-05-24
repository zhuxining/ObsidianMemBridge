"""Integration tests for MemoryService with a temp vault."""

from pathlib import Path

import pytest

from membridge.core import MemoryService
from membridge.models import (
    MemoryFilter,
    MemoryFrontmatter,
    NotFoundError,
    ValidationError,
)
from membridge.settings import Settings


@pytest.fixture()
def svc(tmp_path: Path) -> MemoryService:
    vault = tmp_path / "vault"
    vault.mkdir()
    settings = Settings(vault_root=vault, memories_dir="memories")
    service = MemoryService(settings)
    service.init_vault()
    return service


class TestWriteAndRead:
    def test_write_creates_file(self, svc: MemoryService):
        fm = MemoryFrontmatter(type="fact", source="test")
        doc = svc.write_memory("Hello World", "This is content", fm)
        assert doc.title == "Hello World"
        assert doc.path.endswith(".md")
        assert doc.frontmatter.status == "active"

    def test_read_returns_document(self, svc: MemoryService):
        fm = MemoryFrontmatter(type="fact", source="test")
        written = svc.write_memory("Read Me", "Body", fm)
        doc = svc.read_memory(written.path)
        assert doc.title == "Read Me"
        assert "Body" in doc.content

    def test_read_missing_raises(self, svc: MemoryService):
        with pytest.raises(NotFoundError):
            svc.read_memory("nonexistent.md")


class TestQuery:
    def test_query_by_status(self, svc: MemoryService):
        fm1 = MemoryFrontmatter(type="fact", source="test", status="active")
        fm2 = MemoryFrontmatter(type="fact", source="test", status="archived")
        svc.write_memory("Active", "a", fm1)
        svc.write_memory("Archived", "b", fm2)

        active = svc.query_memories(MemoryFilter(status="active"))
        assert len(active) == 1
        assert active[0].title == "Active"

    def test_query_by_tags(self, svc: MemoryService):
        fm = MemoryFrontmatter(type="note", source="test", tags=["python", "rust"])
        svc.write_memory("Multi-tag", "content", fm)

        found = svc.query_memories(MemoryFilter(tags=["python"]))
        assert len(found) == 1

        not_found = svc.query_memories(MemoryFilter(tags=["go"]))
        assert len(not_found) == 0


class TestUpdate:
    def test_update_status(self, svc: MemoryService):
        fm = MemoryFrontmatter(type="fact", source="test")
        doc = svc.write_memory("Update Me", "body", fm)

        updated = svc.update_memory(doc.path, frontmatter_patch={"status": "archived"})
        assert updated.frontmatter.status == "archived"
        assert updated.frontmatter.updated_at is not None

    def test_update_content(self, svc: MemoryService):
        fm = MemoryFrontmatter(type="fact", source="test")
        doc = svc.write_memory("Content", "original", fm)

        updated = svc.update_memory(doc.path, content="replaced")
        assert "replaced" in updated.content


class TestInit:
    def test_init_requires_vault_root(self, tmp_path: Path):
        settings = Settings()
        svc = MemoryService(settings)
        with pytest.raises(ValidationError, match="vault_root"):
            svc.init_vault()

    def test_init_creates_memories_dir(self, tmp_path: Path):
        vault = tmp_path / "vault"
        vault.mkdir()
        settings = Settings(vault_root=vault, memories_dir="notes")
        svc = MemoryService(settings)
        info = svc.init_vault()
        assert info.memories_dir == "notes"
        assert (vault / "notes").is_dir()
