import pytest
from unified_review import (
    Issue, SummaryReport, issue_dict,
    severity_to_priority, _parse_review_output, _extract_field,
    summary_agent, ReviewResult,
)


class TestIssueDict:
    def test_converts_issue(self):
        i = Issue(type="ai_marker", severity="high", desc="test", fix="del", auto_fixable=True, ch=1)
        d = issue_dict(i)
        assert d["type"] == "ai_marker"
        assert d["auto_fixable"] is True
        assert d["ch"] == 1


class TestSeverityToPriority:
    def test_plagiarism_is_p0(self):
        assert severity_to_priority("medium", "plagiarism") == "P0"

    def test_high_severity_is_p0(self):
        assert severity_to_priority("high", "metaphor") == "P0"

    def test_ai_marker_is_p1(self):
        assert severity_to_priority("medium", "ai_marker") == "P1"

    def test_metaphor_is_p2(self):
        assert severity_to_priority("low", "metaphor") == "P2"


class TestExtractField:
    def test_basic(self):
        result = _extract_field("类型: ai_marker | 严重度: high", "严重度", "medium")
        assert result == "high"

    def test_default_when_missing(self):
        result = _extract_field("类型: ai_marker", "严重度", "medium")
        assert result == "medium"


class TestParseReviewOutput:
    SAMPLE = """### 章节 1
评分: 75
问题:
- 类型: ai_marker | 严重度: high | 描述: 太多路标词 | 修复: 删除

### 跨章问题
- 涉及章节: 1,2,3 | 类型: continuity | 严重度: high | 描述: 连贯性问题 | 修复: 重写部分内容
"""

    def test_parses_chapter(self):
        chapters, _ = _parse_review_output(self.SAMPLE)
        assert "1" in chapters
        assert chapters["1"]["score"] == 75

    def test_parses_chapter_issues(self):
        chapters, _ = _parse_review_output(self.SAMPLE)
        issues = chapters["1"]["issues"]
        assert len(issues) == 1
        assert issues[0]["type"] == "ai_marker"

    def test_parses_cross_issues(self):
        _, cross = _parse_review_output(self.SAMPLE)
        assert len(cross) == 1
        assert cross[0]["type"] == "continuity"

    def test_empty_input(self):
        chapters, cross = _parse_review_output("")
        assert chapters == {}
        assert cross == []


class TestSummaryAgent:
    def test_merges_results(self):
        rr = ReviewResult()
        rr.chapters = {1: {"score": 80, "issues": [{"type": "ai_marker", "severity": "medium", "desc": "marker"}]}}
        report = summary_agent([rr])
        assert 1 in report.chapters
        assert len(report.chapters[1]["issues"]) == 1
        assert report.chapters[1]["issues"][0]["priority"] == "P1"

    def test_empty_input(self):
        report = summary_agent([])
        assert report.chapters == {}
        assert report.stats["total_ch"] == 0
