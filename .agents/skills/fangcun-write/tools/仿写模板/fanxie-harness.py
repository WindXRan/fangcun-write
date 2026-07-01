#!/usr/bin/env python3
"""
仿写 Harness — 全自动批量管线，质量门禁+断点续跑+自动修复。

用法:
    python3 fanxie-harness.py <仿写项目> <起始章> [结束章]

示例:
    python3 fanxie-harness.py 仿写新书 6 10    # 跑第6-10章
    python3 fanxie-harness.py 仿写新书 6        # 从第6章跑到结束
"""

import sys, re, os, json, time
from pathlib import Path

# ─── 配置 ───
SOURCE_BOOK = "全家偷听心声"
MAX_BEAT_CHARS = 400          # 章纲每个beat最大字数
TARGET_WORDS = 2500           # 正文目标字数
WORD_TOLERANCE = 0.30         # 字数容忍度 (±30%)
SOURCE_NAMES = [              # 源文残留检查列表
    "乔娇娇","乔夫人","乔忠国","乔天经","乔地义",
    "孟谷雪","冷面王爷轻点宠","功德商城","功德点","老阎王","阎王"
]
TEMPLATE_MARKERS = [          # guide-convert 模板输出检测
    "替换后的功能标题","替换后的一句话核心事件","（新文章纲XML）"
]
PROGRESS_FILE = "_progress.json"


def log(msg):
    print(f"  {msg}", flush=True)


def load_progress(project):
    p = Path(f"projects/{project}/{PROGRESS_FILE}")
    if p.exists():
        return json.loads(p.read_text())
    return {"done": [], "failed": []}


def save_progress(project, data):
    Path(f"projects/{project}/{PROGRESS_FILE}").write_text(json.dumps(data, ensure_ascii=False))


def check_source_names(text):
    """检查源文残留，返回残留列表"""
    return [n for n in SOURCE_NAMES if n in text]


def is_template_output(text):
    """检测是否为模板输出"""
    return any(m in text for m in TEMPLATE_MARKERS)


def check_word_count(text):
    """检查字数是否在范围内"""
    clean = re.sub(r'<[^>]+>', '', text).strip()
    wc = len(clean)
    lower = int(TARGET_WORDS * (1 - WORD_TOLERANCE))
    upper = int(TARGET_WORDS * (1 + WORD_TOLERANCE))
    return wc, lower <= wc <= upper


def run_tool(name, args, project):
    """运行工具，返回结果文本"""
    sys.path.insert(0, str(Path(".agents/skills/fangcun-write/tools").resolve()))
    from tool_executor import run_tool as _run
    result = _run(name, args, project)
    return result or ""


def main():
    if len(sys.argv) < 2:
        print("用法: python3 fanxie-harness.py <仿写项目> [起始章] [结束章]")
        sys.exit(1)

    project = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end = int(sys.argv[3]) if len(sys.argv) > 3 else 999

    base = Path(f"projects/{project}")
    src_guide = Path(f"projects/{SOURCE_BOOK}/正文/章纲")
    dst_guide = base / "正文" / "章纲"
    dst_text = base / "正文" / "正文"
    src_text = Path(f"projects/{SOURCE_BOOK}/正文/正文")

    # 读取总章数
    import xml.etree.ElementTree as ET
    proj_xml = base / "作品信息" / "project.xml"
    if proj_xml.exists():
        total = int(ET.parse(proj_xml).getroot().findtext("total_chapters") or "200")
        end = min(end, total)
    else:
        end = min(end, 200)

    progress = load_progress(project)
    done = set(progress.get("done", []))
    failed = set(progress.get("failed", []))

    print(f"\n=== 仿写管线: {project} 第{start}-{end}章 ===")
    print(f"   已完: {len(done)}章 | 失败: {len(failed)}章\n")

    for ch in range(start, end + 1):
        if ch in done:
            continue

        print(f"\n--- 第{ch}章 ---")

        # ── Step 0: 确保逆推缓冲区 ──
        guide_file = src_guide / f"第{ch}章.xml"
        if not guide_file.exists():
            log("逆推中...")
            run_tool("source-guide-reverse", {"chapter_number": ch}, f"projects/{SOURCE_BOOK}")

        # ── Step 1: guide-convert（失败自动重试2次） ──
        log("guide-convert...")
        dg = dst_guide / f"第{ch}章.xml"
        # 先copy源章纲
        import shutil
        shutil.copy2(guide_file, dg)
        # 执行转换（最多重试2次）
        for attempt in range(3):
            run_tool("guide-convert", {"chapter_number": ch}, f"projects/{project}")
            if dg.exists():
                text = dg.read_text(encoding="utf-8")
                if not is_template_output(text) and not check_source_names(text):
                    break
            if attempt < 2:
                log(f"模板输出或残留→重试({attempt+1})")
            else:
                log("❌ guide-convert 失败3次，跳过本章")
                failed.add(ch)
                save_progress(project, {"done": list(done), "failed": list(failed)})
                break
        else:
            continue  # 重试耗尽

        # ── Step 2: write-chapter ──
        log("写正文...")
        dt = dst_text / f"第{ch}章.xml"
        run_tool("write-chapter", {"chapter_number": ch}, f"projects/{project}")

        # ── Step 2.5: 修复缺少XML标签的输出 ──
        if dt.exists():
            raw = dt.read_text(encoding='utf-8')
            if '<chapter' not in raw and '<content>' not in raw:
                NL = chr(10)
                if raw.strip().startswith('#'):
                    title = raw.strip().split(chr(10))[0].replace('# ', '').strip()
                else:
                    title = '第' + str(ch) + '章'
                wrapped = '<chapter number="' + str(ch) + '" name="' + title + '">' + chr(10) + '  <content>' + chr(10) + raw.strip() + chr(10) + '  </content>' + chr(10) + '</chapter>'
                dt.write_text(wrapped, encoding='utf-8')                
                log("XML标签已修复")

        # ── Step 3: 质检 ──
        if not dt.exists():
            log("❌ 正文未生成")
            failed.add(ch)
            save_progress(project, {"done": list(done), "failed": list(failed)})
            continue

        text = dt.read_text(encoding="utf-8")

        # 质检查项
        issues = []

        # 3a: 源文残留
        bad = check_source_names(text)
        if bad:
            issues.append(f"源文残留: {bad}")

        # 3b: 字数
        wc, ok = check_word_count(text)
        if not ok:
            issues.append(f"字数{wc}(目标{TARGET_WORDS}±{int(WORD_TOLERANCE*100)}%)")
            # 自动压缩
            log(f"字数{wc}超限，压缩中...")
            run_tool("write-chapter", {"chapter_number": ch, "target_words": TARGET_WORDS}, f"projects/{project}")
            # 重新质检
            if dt.exists():
                text = dt.read_text(encoding="utf-8")
                bad2 = check_source_names(text)
                if bad2:
                    issues.append(f"压缩后残留: {bad2}")
                wc2, ok2 = check_word_count(text)
                if ok2:
                    issues = [i for i in issues if "字数" not in i]

        # 3c: 第三人称视角
        i_lines = sum(1 for l in text.split("\n") if l.strip().startswith("我"))
        if i_lines > 5:
            issues.append(f"第一人称{i_lines}行")

        # 3d: XML完整性
        if "<chapter" not in text or "<content>" not in text:
            issues.append("XML标签缺失")

        if issues:
            log(f"❌ {'; '.join(issues)}")
            failed.add(ch)
        else:
            log(f"✅ {wc}字")
            done.add(ch)

        # 保存进度
        save_progress(project, {"done": list(done), "failed": list(failed)})

    # ── 汇总 ──
    print(f"\n=== 完成: {len(done)}章通过, {len(failed)}章失败 ===")
    if failed:
        print(f"失败章节: {sorted(failed)}")
    save_progress(project, {"done": list(done), "failed": list(failed), "finished": True})


if __name__ == "__main__":
    main()
