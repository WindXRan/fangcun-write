"""导出：章节文件合并为单个 .txt。"""
import re
import os
import sys
from pathlib import Path


def export_book(chapters_dir, output_file=None, header_file=None):
    chapters_path = Path(chapters_dir)
    if not chapters_path.exists():
        print(f"错误: 目录不存在: {chapters_dir}")
        return None

    ch_dir = chapters_path
    if (chapters_path / "chapters").exists():
        ch_dir = chapters_path / "chapters"

    chapter_files = sorted(
        ch_dir.glob("第*.txt"),
        key=lambda p: int(re.search(r"\d+", p.name).group())
    )

    if not chapter_files:
        print(f"错误: 在 {ch_dir} 中未找到章节文件")
        return None

    parent = chapters_path if (chapters_path / "chapters").exists() else chapters_path.parent

    header_path = header_file
    if header_path is None:
        for candidate in [parent / "_header.txt", chapters_path / "_header.txt"]:
            if candidate.exists():
                header_path = candidate
                break

    lines = []
    if header_path and Path(header_path).exists():
        lines.append(Path(header_path).read_text(encoding="utf-8").strip())
        lines.append("")

    for f in chapter_files:
        text = f.read_text(encoding="utf-8").strip()
        lines.append(text)
        lines.append("")

    if output_file is None:
        output_file = parent / f"{parent.name}.txt"

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    print(f"导出完成: {len(chapter_files)} 章 → {output_path}")
    return str(output_path)


def main():
    if len(sys.argv) < 2:
        print("用法: python export_chapters.py <章节目录> [输出文件] [元信息文件]")
        print("示例: python export_chapters.py projects/书名/chapters/")
        print("示例: python export_chapters.py projects/书名/ 输出.txt")
        sys.exit(1)

    chapters_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    header_file = sys.argv[3] if len(sys.argv) > 3 else None
    export_book(chapters_dir, output_file, header_file)


if __name__ == "__main__":
    main()
