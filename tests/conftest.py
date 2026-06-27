"""pytest fixtures for fangcun-write tests."""

import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest


# ── Add project tool paths ──────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TOOLS_DIR = (
    _PROJECT_ROOT
    / ".agents" / "skills" / "fangcun-write" / "tools"
)
_SHARED_TOOLS = _PROJECT_ROOT / ".agents" / "tools"

for p in [_TOOLS_DIR, _SHARED_TOOLS]:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary project directory with expected subdirs."""
    with tempfile.TemporaryDirectory(prefix="fangcun_test_") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "chapters").mkdir(parents=True, exist_ok=True)
        yield tmp_path


@pytest.fixture
def temp_config(temp_project_dir: Path) -> dict:
    """Config pointing at a temporary project directory."""
    return {
        "book_name": "test_book",
        "source_book": "test_source",
        "author": "test_author",
        "model": "deepseek-chat",
        "api_key": "sk-test-key",
        "api_base_url": "https://api.test.com/v1",
        "base_dir": str(_PROJECT_ROOT),
        "project_dir": str(temp_project_dir),
        "workers": 4,
    }
