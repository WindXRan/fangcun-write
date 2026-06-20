"""Phase: 提取 book_data.json（从 concept.md/settings/*.md 提取结构化设定）"""

from pathlib import Path


def phase_extract(config, **kwargs):
    """从 concept.md 或 settings/*.md 提取结构化设定数据，输出 book_data.json。"""
    from extract_book_data import extract

    print(f"\n{'=' * 50}")
    print(f"Phase: 提取 book_data.json")
    print("=" * 50)

    rewrites_dir = Path(config.get("rewrites_dir", ""))
    if not rewrites_dir.exists():
        print(f"  [SKIP] rewrites_dir 不存在: {rewrites_dir}")
        return None

    result = extract(config)
    if result is None:
        print("  [WARN] 提取失败，跳过")
    return result
