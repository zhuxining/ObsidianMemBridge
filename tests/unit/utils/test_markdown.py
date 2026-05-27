"""Unit tests for markdown parsing and serialization."""

from obsidianmembridge.utils.markdown import parse_markdown, serialize_markdown


class TestParseMarkdown:
    def test_with_frontmatter(self):
        text = "---\ntitle: Hello\nstatus: active\n---\nBody here"
        fm, body = parse_markdown(text)
        assert fm == {"title": "Hello", "status": "active"}
        assert body == "Body here"

    def test_without_frontmatter(self):
        text = "Just plain markdown"
        fm, body = parse_markdown(text)
        assert fm == {}
        assert body == "Just plain markdown"

    def test_empty_frontmatter(self):
        text = "---\n---\nBody"
        fm, body = parse_markdown(text)
        assert fm == {}
        assert body == "Body"


class TestSerializeMarkdown:
    def test_roundtrip(self):
        fm = {"title": "Test", "status": "active", "tags": ["a"]}
        body = "# Test\n\nContent"
        serialized = serialize_markdown(fm, body)
        parsed_fm, parsed_body = parse_markdown(serialized)
        assert parsed_fm["title"] == "Test"
        assert parsed_fm["status"] == "active"
        assert parsed_fm["tags"] == ["a"]
        assert parsed_body == body
