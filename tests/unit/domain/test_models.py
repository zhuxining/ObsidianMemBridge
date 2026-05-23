"""Unit tests for domain models, validation, and errors."""

from datetime import datetime, timezone

import pytest

from membridge.domain.errors import MemBridgeError, NotFoundError, ValidationError
from membridge.domain.models import MemoryFilter, MemoryFrontmatter
from membridge.domain.validation import check_sensitive_keys, validate_frontmatter_required


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
        now = datetime.now(timezone.utc)
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
        fm = MemoryFrontmatter(
            type="fact",
            source="codex",
            custom_key="hello",
        )
        assert fm.custom_key == "hello"


# -- filter model -------------------------------------------------------------

class TestMemoryFilter:
    def test_empty(self):
        f = MemoryFilter()
        assert f.status is None
        assert f.tags == []

    def test_with_tags(self):
        f = MemoryFilter(tags=["python", "rust"])
        assert "python" in f.tags


# -- validation ---------------------------------------------------------------

class TestValidateFrontmatterRequired:
    def test_valid(self):
        validate_frontmatter_required({
            "status": "active",
            "type": "fact",
            "source": "codex",
            "created_at": datetime.now(timezone.utc),
        })

    def test_missing_key(self):
        with pytest.raises(ValidationError, match="Missing required"):
            validate_frontmatter_required({"status": "active"})

    def test_invalid_status(self):
        with pytest.raises(ValidationError, match="Invalid status"):
            validate_frontmatter_required({
                "status": "deleted",
                "type": "fact",
                "source": "codex",
                "created_at": datetime.now(timezone.utc),
            })


class TestCheckSensitiveKeys:
    def test_clean(self):
        assert check_sensitive_keys({"title": "hello", "type": "fact"}) == []

    def test_detects_api_key(self):
        found = check_sensitive_keys({"api_key": "sk-123", "title": "test"})
        assert len(found) == 1

    def test_detects_password(self):
        found = check_sensitive_keys({"password": "secret"})
        assert len(found) == 1
