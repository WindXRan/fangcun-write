"""迁移 novel-download-authors/ → projects/，按作者合并，同名 dedup."""

import os
import shutil
import hashlib
import sys
from pathlib import Path

BASE = Path(os.environ.get("PROJECT_ROOT", Path(__file__).parent.parent))
SRC = BASE / "novel-download-authors"
DST = BASE / "projects"


def file_hash(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def move_book_chapters(author, book_name, src_dir, dry_run=False):
    """Move chapter files from src_dir to projects/{author}/{book_name}/_cache/chapters/"""
    cache_dir = DST / author / book_name / "_cache" / "chapters"
    cache_dir.mkdir(parents=True, exist_ok=True)

    moved = 0
    skipped = 0
    for f in sorted(os.listdir(src_dir)):
        src_path = Path(src_dir) / f
        if not src_path.is_file():
            continue
        dst_path = cache_dir / f
        if dst_path.exists():
            if dst_path.stat().st_size == src_path.stat().st_size and dst_path.stat().st_mtime_ns == src_path.stat().st_mtime_ns:
                skipped += 1
                continue
            # Different file — add suffix
            stem = dst_path.stem
            ext = dst_path.suffix
            dst_path = cache_dir / f"{stem}_from_download{ext}"

        if dry_run:
            moved += 1
            continue
        shutil.copy2(src_path, dst_path)
        moved += 1
    return moved, skipped


def handle_book_txt(author, book_name, txt_path, dry_run=False):
    """Move full-book .txt to projects/{author}/{book_name}/_cache/"""
    cache_dir = DST / author / book_name / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    dst = cache_dir / txt_path.name
    if dst.exists():
        if dst.stat().st_size == txt_path.stat().st_size and dst.stat().st_mtime_ns == txt_path.stat().st_mtime_ns:
            return "identical (skip)", 0
        dst = cache_dir / f"{txt_path.stem}_from_download{txt_path.suffix}"

    if not dry_run:
        shutil.copy2(txt_path, dst)
    return f"copied to {dst.name}", 1


def migrate(dry_run=False):
    total_copied = 0
    results = []

    for author in sorted(os.listdir(SRC)):
        author_src = SRC / author
        if not author_src.is_dir():
            continue

        # Create author dir in projects if needed
        author_dst = DST / author
        if not author_dst.exists() and not dry_run:
            author_dst.mkdir(parents=True, exist_ok=True)

        for item in sorted(os.listdir(author_src)):
            item_path = author_src / item
            if item_path.is_dir():
                # Book chapter directory
                # Try to find corresponding .txt for the book name
                book_txt = author_src / f"{item}.txt"
                if book_txt.exists():
                    result, n = handle_book_txt(author, item, book_txt, dry_run)
                    if n:
                        total_copied += n
                    results.append(f"  TXT [{item}.txt] -> {result}")

                result, n = move_book_chapters(author, item, item_path, dry_run)
                total_copied += n
                results.append(f"  DIR [{item}/] -> moved {n} chapters, skipped existing")
            elif item.endswith(".txt"):
                # Standalone full-book txt — determine book name from filename
                book_name = item[:-4]
                # Check if there's a matching dir already handled
                # If the author already has this book in projects, dedup
                book_dst = DST / author / book_name
                if book_dst.exists():
                    result, n = handle_book_txt(author, book_name, item_path, dry_run)
                    total_copied += n
                    results.append(f"  TXT [{item}] -> {result}")
                else:
                    # New book: create dir + copy txt to _cache
                    cache_dir = book_dst / "_cache"
                    dst = cache_dir / item
                    if dst.exists():
                        if dst.stat().st_size == item_path.stat().st_size and dst.stat().st_mtime_ns == item_path.stat().st_mtime_ns:
                            results.append(f"  TXT [{item}] -> identical (skip)")
                            continue
                        dst = cache_dir / f"{book_name}_from_download.txt"
                    if not dry_run:
                        cache_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item_path, dst)
                    total_copied += 1
                    results.append(f"  TXT [{item}] -> copied to {dst.relative_to(DST)}")
            elif item.endswith(".json"):
                # Style profile JSON — copy to rewrites dir
                # Determine which book it belongs to
                book_name = item.replace("_style_profile.json", "")
                book_rewrite_dir = DST / author / book_name / "rewrites" / f"{book_name}仿写"
                if book_rewrite_dir.exists() and not dry_run:
                    shutil.copy2(item_path, book_rewrite_dir / item)
                    results.append(f"  JSON [{item}] -> copied to rewrites/")
                else:
                    # Keep in _cache for now
                    cache_dir = DST / author / book_name / "_cache"
                    if not dry_run:
                        cache_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item_path, cache_dir / item)
                    results.append(f"  JSON [{item}] -> copied to _cache/")

    return total_copied, results


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    total, results = migrate(dry_run=dry)
    print(f"\n{'DRY RUN' if dry else 'MIGRATION'} complete — {total} files copied\n")
    for r in results:
        print(r)
