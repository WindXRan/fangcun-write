import pytest
from prompt_loader import extract_file_refs, embed_files, EMBED_TAGS


class TestExtractFileRefs:
    def test_single_ref(self):
        refs = extract_file_refs("【源文】path/to/file.md")
        assert len(refs) == 1
        assert refs[0][0] == "源文"
        assert refs[0][1] == "path/to/file.md"

    def test_multiple_refs(self):
        text = "【源文】a.md\n【设定】b.md"
        refs = extract_file_refs(text)
        assert len(refs) == 2

    def test_no_refs(self):
        assert extract_file_refs("plain text") == []

    def test_tag_without_path(self):
        assert extract_file_refs("【源文】") == []


class TestEmbedFiles:
    def test_embeds_content_from_file(self, tmp_path):
        src = tmp_path / "test.md"
        src.write_text("embedded content", encoding="utf-8")
        result = embed_files("【源文】test.md", str(tmp_path))
        assert "embedded content" in result
        assert "test.md" in result

    def test_nonexistent_file_shows_warning(self, tmp_path):
        result = embed_files("【源文】missing.md", str(tmp_path))
        assert "文件不存在" in result

    def test_non_embed_tag_not_modified(self):
        result = embed_files("【输出】path/to/file.md", "/tmp")
        assert result == "【输出】path/to/file.md"

    def test_replacements_applied(self):
        result = embed_files("hello {name}", "/tmp", {"name": "world"})
        assert result == "hello world"

    def test_chinese_tag(self):
        result = embed_files("【模板】nonexistent_template.md", "/tmp")
        assert "模板" in result
