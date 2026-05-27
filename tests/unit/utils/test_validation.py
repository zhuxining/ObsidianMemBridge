"""Unit tests for frontmatter validation utilities."""

from datetime import UTC, datetime

from obsidianmembridge.models import ValidationError
from obsidianmembridge.utils.validation import check_sensitive_keys, validate_frontmatter_required
import pytest


class TestValidateFrontmatterRequired:
    def test_valid(self):
        validate_frontmatter_required({
            "status": "active",
            "type": "fact",
            "source": "codex",
            "created_at": datetime.now(UTC),
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
                "created_at": datetime.now(UTC),
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
