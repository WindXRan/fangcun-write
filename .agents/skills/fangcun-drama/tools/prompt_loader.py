"""
Prompt 加载器 — 从 prompts/ 目录加载 prompt 文件。
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """加载 prompt 文件，返回纯文本内容。

    Args:
        name: prompt 文件名，如 "skeleton.md", "event_extraction.md"

    Returns:
        str: prompt 文本内容
    """
    p = PROMPTS_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {p}")
    return p.read_text(encoding="utf-8")


def list_prompts() -> list[str]:
    """列出所有可用的 prompt 文件名。"""
    return [f.name for f in sorted(PROMPTS_DIR.glob("*.md"))]
