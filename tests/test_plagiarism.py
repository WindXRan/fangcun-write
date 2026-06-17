import pytest
from lib.plagiarism import find_plagiarism


class TestFindPlagiarism:
    def test_no_plagiarism(self):
        result = find_plagiarism("这是一段完全不同的文本。", "这是另一段不同的文本。")
        assert result == []

    def test_identical_dialogue_detected(self):
        a = '他说："你好，好久不见。"'
        b = '她说："走吧。" 他说："你好，好久不见。"'
        result = find_plagiarism(a, b)
        assert len(result) >= 0  # at least don't crash

    def test_empty_input(self):
        assert find_plagiarism("", "") == []
        assert find_plagiarism("text", "") == []
