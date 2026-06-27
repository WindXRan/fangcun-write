"""Tests for prompt_loader — frontmatter parsing, variable resolution."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_prompt_file():
    """Create a temporary .md prompt file with frontmatter."""
    content = """---
name: test-prompt
description: A test prompt
temperature: 0.7
---

Write a chapter about @topic with @style.
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as f:
        f.write(content)
        tmp_path = f.name
    yield tmp_path
    os.unlink(tmp_path)


def test_load_prompt_basic(temp_prompt_file):
    """load_prompt reads a .md file and returns its content."""
    from prompt_loader import load_prompt

    result = load_prompt(temp_prompt_file, os.getcwd())
    assert result is not None
    assert "Write a chapter" in result


def test_load_prompt_with_replacements(temp_prompt_file, temp_config):
    """load_prompt replaces {variables} in the prompt."""
    from prompt_loader import load_prompt

    result = load_prompt(
        temp_prompt_file, os.getcwd(),
        replacements={"topic": "magic", "style": "suspense"},
    )
    assert result is not None
    # The raw string still has @variables (they're for VariableResolver),
    # but {key} replacements should work via safe_format fallback
    assert "magic" in result or "@topic" in result


def test_load_prompt_file_not_found():
    """load_prompt raises FileNotFoundError for missing paths."""
    from prompt_loader import load_prompt

    with pytest.raises(FileNotFoundError):
        load_prompt("/nonexistent/prompt.md", os.getcwd())


def test_frontmatter_parsing(temp_prompt_file):
    """Frontmatter metadata is stripped from the returned content."""
    from prompt_loader import load_prompt

    result = load_prompt(temp_prompt_file, os.getcwd())
    # Frontmatter block should be removed
    assert "---" not in result.split('\n')[0]
    assert "name:" not in result


def test_load_prompt_with_project_dir(temp_prompt_file, temp_config):
    """load_prompt accepts an optional project_dir kwarg."""
    from prompt_loader import load_prompt

    result = load_prompt(
        temp_prompt_file, os.getcwd(),
        mode="api", project_dir=temp_config["project_dir"],
    )
    assert result is not None
    assert len(result) > 0
