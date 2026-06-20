"""出海引擎：中文章节 → 英文翻译 → Webnovel/Wattpad 格式导出。

用法：
  python overseas.py --config configs/xxx.json --start 1 --end 100
  python overseas.py --config configs/xxx.json --export webnovel
"""

import os
import re
import json
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "fangcun-novel" / "tools"))

from utils import call_api, get_source_text
from prompt_loader import load_prompt_str, get_prompt_config_with_overrides


def translate_chapter(config, ch, api_key, api_url, model):
    """翻译单章：中文章 → 英文章。"""
    chapters_dir = Path(config["rewrites_dir"]) / "chapters"
    en_dir = Path(config["rewrites_dir"]) / "chapters_en"
    en_dir.mkdir(parents=True, exist_ok=True)

    ch_file = chapters_dir / f"ch_{ch:03d}.txt"
    if not ch_file.exists():
        return None

    # 检查缓存
    en_file = en_dir / f"ch_{ch:03d}.txt"
    if en_file.exists() and en_file.stat().st_size > 500:
        return en_file

    # 读取中文原文
    zh_text = ch_file.read_text(encoding="utf-8")

    # 加载术语表
    glossary_path = Path(config["rewrites_dir"]) / "glossary.json"
    glossary = {}
    if glossary_path.exists():
        glossary = json.loads(glossary_path.read_text(encoding="utf-8"))

    # 构建 prompt
    prompt_template = load_prompt_str("translate-chapter.md")
    if not prompt_template:
        # 使用默认 prompt
        prompt_template = """将以下中文章节翻译成英文，适配 Webnovel 平台风格。

翻译规则：
1. 对话直译，保持原文的对话节奏和语气
2. 叙述意译，用英文网文习惯重写
3. 文化适配，中式表达改成英文读者能理解的方式
4. 术语一致，人名/地名按术语表翻译
5. 风格保留，保持原文的句式节奏

格式：
- 每章 1500-3000 词
- 标题格式：Chapter {N}: {{Title}}
- 段落之间空行分隔
- 无中文标点

术语表：
{glossary}

中文原文：
{zh_text}"""

    prompt = prompt_template.format(
        N=ch,
        glossary=json.dumps(glossary, ensure_ascii=False, indent=2) if glossary else "（无术语表）",
        zh_text=zh_text[:6000],  # 限制长度，避免超 token
    )

    pc = get_prompt_config_with_overrides("translate-chapter.md", config)
    system_prompt = "你是专业的中英文学翻译，擅长将中文网文翻译成英文 Webnovel 风格。"

    try:
        result = call_api(
            api_key, pc.get("model", model), prompt,
            reasoning_effort=pc.get("reasoning_effort", "high"),
            max_tokens=pc.get("max_tokens", 8192),
            temperature=pc.get("temperature", 0.7),
            system_prompt=system_prompt, api_url=api_url,
        )

        # 保存翻译结果
        en_file.write_text(result, encoding="utf-8")
        print(f"  [TRANSLATE] ch{ch:03d}")
        return en_file
    except Exception as e:
        print(f"  [FAIL] translate ch{ch}: {e}")
        return None


def build_glossary(config):
    """从 book_data.json 构建术语表。"""
    book_data_path = Path(config["rewrites_dir"]) / "book_data.json"
    if not book_data_path.exists():
        return {}

    data = json.loads(book_data_path.read_text(encoding="utf-8"))
    glossary = {}

    # 角色名
    for char in data.get("characters", []):
        name = char.get("name", "")
        if name:
            # 简单音译规则（可扩展）
            glossary[name] = _transliterate(name)

    # 地名
    book_info = data.get("book_info", {})
    if book_info.get("location"):
        glossary[book_info["location"]] = _transliterate(book_info["location"])

    return glossary


def _transliterate(chinese_name):
    """简单音译（实际应用需要更完善的拼音转换）。"""
    # 这里只是占位，实际需要拼音转换库
    return chinese_name  # 暂时保留原名


def export_webnovel(config, start, end):
    """导出 Webnovel 格式。"""
    en_dir = Path(config["rewrites_dir"]) / "chapters_en"
    export_dir = Path(config["rewrites_dir"]) / "export" / "webnovel"
    export_dir.mkdir(parents=True, exist_ok=True)

    book_name = config.get("book_name", "Untitled")
    exported = 0

    for ch in range(start, end + 1):
        en_file = en_dir / f"ch_{ch:03d}.txt"
        if not en_file.exists():
            continue

        text = en_file.read_text(encoding="utf-8")

        # 格式化为 Webnovel 格式
        lines = text.strip().split("\n")
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue

            # 标题格式化
            if line.startswith("第") and "章" in line[:10]:
                # 提取章号和标题
                m = re.match(r"第(\d+)章\s*(.*)", line)
                if m:
                    ch_num = m.group(1)
                    title = m.group(2) or f"Chapter {ch_num}"
                    formatted_lines.append(f"Chapter {ch_num}: {title}")
                    formatted_lines.append("")
                    continue

            # 替换中文标点
            line = line.replace("，", ", ").replace("。", ". ")
            line = line.replace("！", "! ").replace("？", "? ")
            line = line.replace(""", '"').replace(""", '"')
            line = line.replace("'", "'").replace("'", "'")
            line = line.replace("：", ": ").replace("；", "; ")
            line = line.replace("（", "(").replace("）", ")")

            formatted_lines.append(line)

        # 写入导出文件
        export_file = export_dir / f"chapter_{ch}.txt"
        export_file.write_text("\n".join(formatted_lines), encoding="utf-8")
        exported += 1

    print(f"[OK] 导出 {exported} 章到 {export_dir}")
    return exported


def main():
    parser = argparse.ArgumentParser(description="出海引擎：中文章节翻译成英文")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--start", type=int, default=1, help="起始章")
    parser.add_argument("--end", type=int, default=100, help="结束章")
    parser.add_argument("--workers", type=int, default=5, help="并行数")
    parser.add_argument("--export", choices=["webnovel", "wattpad"], help="导出格式")
    parser.add_argument("--build-glossary", action="store_true", help="构建术语表")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))

    # 构建术语表
    if args.build_glossary:
        glossary = build_glossary(config)
        glossary_path = Path(config["rewrites_dir"]) / "glossary.json"
        glossary_path.write_text(json.dumps(glossary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] 术语表 → {glossary_path}")
        return

    # 导出
    if args.export:
        export_webnovel(config, args.start, args.end)
        return

    # 翻译
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        print("[FAIL] 未设置 API_KEY")
        return

    from lib.api_client import get_api_url
    api_url = get_api_url(config)
    model = config.get("model", "deepseek-v4-flash")

    print(f"\n{'=' * 50}")
    print(f"出海引擎 | ch{args.start}-{args.end} | {args.workers}w")
    print("=" * 50)

    # 构建术语表
    glossary = build_glossary(config)
    glossary_path = Path(config["rewrites_dir"]) / "glossary.json"
    glossary_path.write_text(json.dumps(glossary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"术语表: {len(glossary)} 条")

    # 并行翻译
    t0 = time.time()
    translated = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(translate_chapter, config, ch, api_key, api_url, model): ch 
                   for ch in range(args.start, args.end + 1)}
        for f in as_completed(futures):
            if f.result():
                translated += 1

    print(f"\n完成: {translated}/{args.end - args.start + 1} 章 | 耗时 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    import time
    main()
