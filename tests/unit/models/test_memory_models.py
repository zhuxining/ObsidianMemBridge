"""Unit tests for memory models and errors."""

from datetime import UTC, datetime

from membridge.models import (
    MemBridgeError,
    MemoryFilter,
    MemoryFrontmatter,
    NotFoundError,
    ValidationError,
)

# -- errors -------------------------------------------------------------------


class TestErrors:
    def test_validation_error_is_membridge_error(self):
        assert issubclass(ValidationError, MemBridgeError)

    def test_not_found_error_is_membridge_error(self):
        assert issubclass(NotFoundError, MemBridgeError)


# -- frontmatter model --------------------------------------------------------


class TestMemoryFrontmatter:
    def test_minimal(self):
        fm = MemoryFrontmatter(type="fact", source="codex")
        assert fm.status == "active"
        assert fm.tags == []
        assert fm.scope is None

    def test_full(self):
        now = datetime.now(UTC)
        fm = MemoryFrontmatter(
            status="archived",
            type="note",
            source="manual",
            created_at=now,
            scope="personal",
            project="test",
            tags=["a", "b"],
            updated_at=now,
        )
        assert fm.status == "archived"
        assert fm.project == "test"
        assert fm.tags == ["a", "b"]

    def test_extra_fields_allowed(self):
        fm = MemoryFrontmatter.model_validate({
            "type": "fact",
            "source": "codex",
            "custom_key": "hello",
        })
        assert fm.model_extra is not None
        assert fm.model_extra["custom_key"] == "hello"


# -- filter model -------------------------------------------------------------


class TestMemoryFilter:
    def test_empty(self):
        f = MemoryFilter()
        assert f.status is None
        assert f.tags == []

    def test_with_tags(self):
        f = MemoryFilter(tags=["python", "rust"])
        assert "python" in f.tags
