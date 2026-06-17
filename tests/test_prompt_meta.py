import pytest
from prompt_meta import safe_format, _parse_frontmatter, get_prompt_meta, validate_prompt_variables


class TestSafeFormat:
    def test_basic_substitution(self):
        assert safe_format("hello {name}", {"name": "world"}) == "hello world"

    def test_missing_key_left_untouched(self):
        assert safe_format("{a} {b}", {"a": "x"}) == "x {b}"

    def test_content_with_braces_no_crash(self):
        result = safe_format("{content} here", {"content": "text with {braces}"})
        assert result == "text with {braces} here"

    def test_multiple_replacements(self):
        assert safe_format("{a}{b}{c}", {"a": "1", "b": "2", "c": "3"}) == "123"

    def test_empty_replacements(self):
        assert safe_format("hello {name}", {}) == "hello {name}"

    def test_overlapping_keys(self):
        assert safe_format("{k}{key}", {"k": "a", "key": "b"}) == "ab"

    def test_digit_values(self):
        assert safe_format("count: {n}", {"n": 42}) == "count: 42"

    def test_chinese_keys(self):
        assert safe_format("书名：{新书名}", {"新书名": "测试"}) == "书名：测试"


class TestParseFrontmatter:
    SAMPLE = """---
version: 3
changelog: test
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-pro", "temperature": 0.8}
required_vars: ["content"]
---

body text
"""

    def test_parses_version(self):
        meta, body = _parse_frontmatter(self.SAMPLE)
        assert meta["version"] == 3

    def test_parses_string_fields(self):
        meta, _ = _parse_frontmatter(self.SAMPLE)
        assert meta["changelog"] == "test"
        assert meta["system_prompt"] == "system-generic.md"

    def test_parses_json_defaults(self):
        meta, _ = _parse_frontmatter(self.SAMPLE)
        assert meta["defaults"] == {"model": "deepseek-v4-pro", "temperature": 0.8}

    def test_parses_json_array(self):
        meta, _ = _parse_frontmatter(self.SAMPLE)
        assert meta["required_vars"] == ["content"]

    def test_body_extracted(self):
        _, body = _parse_frontmatter(self.SAMPLE)
        assert "body text" in body

    def test_no_frontmatter(self):
        meta, body = _parse_frontmatter("just body")
        assert meta["version"] == 1
        assert body == "just body"

    def test_boolean_field(self):
        meta, _ = _parse_frontmatter("---\nflag: true\n---\nbody")
        assert meta["flag"] is True

    def test_malformed_json_falls_back_to_string(self):
        meta, _ = _parse_frontmatter('---\ndefaults: {bad json}\n---\nbody')
        assert isinstance(meta["defaults"], str)

    def test_bom_stripped(self):
        meta, body = _parse_frontmatter('\ufeff---\nversion: 2\n---\nbody')
        assert meta["version"] == 2
        assert body == "body"


class TestGetPromptMeta:
    def test_returns_empty_for_nonexistent(self):
        from prompt_meta import _PROMPTS_DIR
        meta = get_prompt_meta("nonexistent_file.md")
        assert meta == {}

    def test_parses_real_prompt_file(self):
        meta = get_prompt_meta("write-chapter.md")
        assert meta.get("version", 0) >= 1
        assert meta.get("system_prompt") is not None


class TestValidatePromptVariables:
    def test_no_required_vars_ok(self):
        validate_prompt_variables("system-generic.md", {})  # should not raise

    def test_missing_required_var_raises(self):
        with pytest.raises(ValueError, match="缺少必要变量"):
            validate_prompt_variables("expand-chapter.md", {})
