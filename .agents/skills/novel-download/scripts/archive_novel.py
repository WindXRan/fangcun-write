import re, shutil, sys
from pathlib import Path

def archive_novel(txt_path, authors_root="authors"):
    txt_path = Path(txt_path)
    if not txt_path.exists():
        return None, f"文件不存在: {txt_path}"
    with open(txt_path, "r", encoding="utf-8") as f:
        head = f.read(500)
    match = re.search(r"作者[：:]\s*(.+)", head)
    if not match:
        return None, "未找到作者名"
    author = match.group(1).strip()
    author_dir = Path(authors_root) / author
    author_dir.mkdir(parents=True, exist_ok=True)
    dest = author_dir / txt_path.name
    if dest.exists():
        dest.unlink()
    shutil.move(str(txt_path), str(dest))
    return dest, f"已归档到 {dest}"

def archive_all_in_dir(download_dir, authors_root="authors"):
    download_dir = Path(download_dir)
    for txt_file in download_dir.glob("*.txt"):
        dest, msg = archive_novel(txt_file, authors_root)
        print(f"  {txt_file.name}: {msg}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python archive_novel.py <txt文件或目录>")
        sys.exit(1)
    target = Path(sys.argv[1])
    if target.is_file():
        dest, msg = archive_novel(target)
        print(msg)
    elif target.is_dir():
        archive_all_in_dir(target)
    else:
        print(f"路径不存在: {target}")