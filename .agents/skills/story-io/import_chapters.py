"""导入：txt拆章 + 提取元信息。"""
import re
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fangcun-write" / "tools"))
from split_chapters_generic import split_chapters


def import_book(input_file, output_dir=None):
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"错误: 文件不存在: {input_file}")
        return None

    if output_dir is None:
        output_dir = input_path.parent / input_path.stem
    else:
        output_dir = Path(output_dir)

    chapters_dir = output_dir / "chapters"
    os.makedirs(chapters_dir, exist_ok=True)

    content = input_path.read_text(encoding="utf-8")

    header_lines = []
    body_start = 0
    for i, line in enumerate(content.split("\n")):
        if re.match(r"第\d+章\s", line):
            body_start = content.index(line)
            break
        header_lines.append(line)

    header = "\n".join(header_lines).strip()

    (output_dir / "_header.txt").write_text(header, encoding="utf-8")

    book_name = ""
    author = ""
    for line in header_lines:
        if line.startswith("书名："):
            book_name = line.replace("书名：", "").strip()
        elif line.startswith("作者："):
            author = line.replace("作者：", "").strip()

    chapter_count = split_chapters(str(input_path), str(chapters_dir))

    toc_path = str(chapters_dir / "_toc.txt")
    toc_lines = []
    for ch in sorted(chapters_dir.glob("第*.txt"), key=lambda p: int(re.search(r"\d+", p.name).group())):
        first_line = ch.read_text(encoding="utf-8").split("\n")[0].strip()
        toc_lines.append(first_line)
    Path(toc_path).write_text("\n".join(toc_lines), encoding="utf-8")

    print(f"\n导入完成:")
    print(f"  书名: {book_name or '(未提取)'}")
    print(f"  作者: {author or '(未提取)'}")
    print(f"  章节: {chapter_count} 章")
    print(f"  输出: {output_dir}")
    return output_dir


def main():
    if len(sys.argv) < 2:
        print("用法: python import_chapters.py <输入文件> [输出目录]")
        print("示例: python import_chapters.py 小说.txt")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    import_book(input_file, output_dir)


if __name__ == "__main__":
    main()
