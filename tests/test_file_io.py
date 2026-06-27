"""Tests for file_io and utility functions — path construction, chapter save/load."""

import os
from pathlib import Path

import pytest


def test_save_chapter_file(temp_project_dir):
    """save_chapter_file writes to chapters/ and removes old ch_XXX format."""
    from utils import save_chapter_file

    project_dir = str(temp_project_dir)
    chapters_dir = temp_project_dir / "chapters"
    chapters_dir.mkdir(exist_ok=True)

    # Create an old-format file to simulate upgrade
    old_file = chapters_dir / "ch_001.txt"
    old_file.write_text("old content", encoding="utf-8")

    # Save new format
    text = "## 第一章 测试\n\nContent body."
    fname = save_chapter_file(project_dir, 1, text)

    # Old format file should be deleted
    assert not old_file.exists()
    # New format file should exist (title extraction may vary)
    assert (chapters_dir / fname).exists()
    assert str(1) in fname


def test_find_chapter_file(temp_project_dir):
    """find_chapter_file locates chapter by number."""
    from utils import find_chapter_file

    chapters_dir = temp_project_dir / "chapters"
    ch_file = chapters_dir / "第5章 转折.txt"
    ch_file.write_text("content", encoding="utf-8")

    found = find_chapter_file(str(temp_project_dir), 5)
    assert found is not None
    assert found.name == "第5章 转折.txt"


def test_load_chapter_text(temp_project_dir):
    """load_chapter_text reads the chapter file content."""
    from utils import load_chapter_text, save_chapter_file

    project_dir = str(temp_project_dir)
    text = "## 第3章 暗流\n\nSome content."
    save_chapter_file(project_dir, 3, text)

    loaded = load_chapter_text(project_dir, 3)
    assert "暗流" in loaded
    assert "content" in loaded.lower()


def test_load_chapter_text_not_found(temp_project_dir):
    """load_chapter_text raises FileNotFoundError for missing chapter."""
    from utils import load_chapter_text

    with pytest.raises(FileNotFoundError):
        load_chapter_text(str(temp_project_dir), 999)


def test_clear_cache(temp_config):
    """clear_cache runs without error."""
    from utils import clear_cache, get_cache_stats

    stats_before = get_cache_stats(temp_config)
    clear_cache()
    stats_after = get_cache_stats(temp_config)
    assert stats_after.get("memory (total keys)", 0) == 0
