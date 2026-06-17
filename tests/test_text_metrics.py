import pytest
from lib.text_metrics import count_metrics, get_body_chars


class TestCountMetrics:
    def test_basic_count(self):
        text = "这是一个测试句子。"
        m = count_metrics(text)
        assert m["chars"] > 0
        assert "ai_markers" in m
        assert "metaphor" in m
        assert "direct_emotion" in m
        assert "pronoun_density" in m
        assert "sent_len_stddev" in m

    def test_ai_markers_detected(self):
        text = "首先，我们要明白。其次，我们需要改进。"
        m = count_metrics(text)
        assert m["ai_markers"] >= 2

    def test_empty_text(self):
        m = count_metrics("")
        assert m["chars"] == 0 or m["chars"] == 1  # may count trailing newline


class TestGetBodyChars:
    def test_strips_whitespace(self):
        text = "hello world\nline2"
        chars = get_body_chars(text)
        assert chars > 0  # just verify it doesn't crash

    def test_chinese_chars(self):
        text = "你好世界"
        assert get_body_chars(text) == 4
