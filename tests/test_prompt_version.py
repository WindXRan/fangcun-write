import pytest
from prompt_version import tag_output, get_output_path, prompt_tag, bump_prompt_version


class TestTagOutput:
    def test_appends_tag(self):
        result = tag_output("hello", "write-chapter.md")
        assert result.startswith("hello")
        assert "prompt:" in result
        assert result.endswith("\n")

    def test_strips_trailing_newlines(self):
        result = tag_output("hello\n\n", "write-chapter.md")
        assert result.count("hello") == 1


class TestGetOutputPath:
    def test_extracts_path(self):
        result = get_output_path("【输出】chapters/ch_001.txt")
        assert result == "chapters/ch_001.txt"

    def test_none_when_no_match(self):
        assert get_output_path("no output tag") is None

    def test_with_replacements(self):
        result = get_output_path("【输出】ch_{n}.txt", {"n": "001"})
        assert result == "ch_001.txt"


class TestPromptTag:
    def test_generates_html_comment(self):
        tag = prompt_tag("write-chapter.md")
        assert tag.startswith("<!--")
        assert tag.endswith("-->")
