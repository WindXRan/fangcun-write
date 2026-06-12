"""Phase 4: 对比 + 版本聚合"""

import os
import re
import subprocess
from pathlib import Path


def phase_compare(config, start, end, batch_size=10):
    """生成仿写 vs 源文对比报告 + 版本聚合"""
    rewrites_dir = config["rewrites_dir"]
    compare_dir = f"{rewrites_dir}/compare"
    compare_script = ".agents/skills/story-compare/compare.py"

    print(f"\n{'=' * 50}")
    print(f"Phase 4: 对比 (ch{start}-{end}, 每{batch_size}章一批)")
    print("=" * 50)

    # 清理旧的对比报告
    for old_file in Path(compare_dir).glob("对比_*.md"):
        old_file.unlink()
    for old_file in Path(compare_dir).glob("源文_*.txt"):
        old_file.unlink()
    for old_file in Path(compare_dir).glob("新书_*.txt"):
        old_file.unlink()
    print("已清理旧对比报告")

    # 分批处理
    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end)
        print(f"\n  对比第{batch_start}-{batch_end}章...")

        cmd = ["python", compare_script, rewrites_dir, str(batch_start), str(batch_end)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=120)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

            print(f"  [OK] 对比_{batch_start}-{batch_end}_报告.md")
            print(f"  [OK] 对比_{batch_start}-{batch_end}_AI分析.md")
        except Exception as e:
            print(f"  [FAIL] 第{batch_start}-{batch_end}章对比失败: {e}")
            continue

    # 版本聚合
    _write_version_report(rewrites_dir, compare_dir)

    print(f"\n对比报告 → {rewrites_dir}/compare/")


# ============================================================
# 版本聚合
# ============================================================

_TAG_RE = re.compile(r'<!-- prompt:\s*([\w.-]+)@(\d+)\s*-->')


def _collect_version_stats(rewrites_dir):
    """扫描 chapters/，从末行提取 prompt 版本 tag，按 (prompt_name, version) 聚合。"""
    chapters_dir = Path(rewrites_dir) / "chapters"
    if not chapters_dir.exists():
        return {}

    groups = {}  # key: f"{prompt_name}@{version}" → {chapters: [], count: N, prompt_name, version}
    for ch_file in sorted(chapters_dir.glob("ch_*.txt")):
        try:
            last_line = ch_file.read_text(encoding="utf-8").strip().split("\n")[-1]
        except Exception:
            continue
        m = _TAG_RE.search(last_line)
        if not m:
            continue
        name, ver = m.group(1), int(m.group(2))
        key = f"{name}@{ver}"
        if key not in groups:
            groups[key] = {"prompt_name": name, "version": ver, "chapters": []}
        groups[key]["chapters"].append(int(ch_file.stem.split("_")[1]))
        groups[key]["count"] = len(groups[key]["chapters"])  # 动态计算

    return groups


def _write_version_report(rewrites_dir, compare_dir):
    """写入版本聚合报告 对比_版本聚合.md"""
    groups = _collect_version_stats(rewrites_dir)
    if not groups:
        return

    out_path = Path(compare_dir) / "对比_版本聚合.md"
    lines = []
    lines.append("# Prompt 版本聚合\n")
    lines.append(f"共扫描到 {sum(g['count'] for g in groups.values())} 章含版本 tag\n\n")

    # 按版本分组展示
    for key in sorted(groups.keys()):
        g = groups[key]
        ch_range = g["chapters"]
        lines.append(f"## {key}（{g['count']} 章）\n")
        lines.append(f"| 属性 | 值 |\n|------|-----|\n")
        lines.append(f"| prompt | {g['prompt_name']} |\n")
        lines.append(f"| 版本 | {g['version']} |\n")
        lines.append(f"| 章节数 | {g['count']} |\n")
        lines.append(f"| 章节范围 | {min(ch_range)}-{max(ch_range)} |\n")

        # 连续区间可视化
        sorted_chs = sorted(ch_range)
        ranges = []
        start = sorted_chs[0]
        end = sorted_chs[0]
        for ch in sorted_chs[1:]:
            if ch == end + 1:
                end = ch
            else:
                ranges.append(f"{start}-{end}" if start != end else str(start))
                start = end = ch
        ranges.append(f"{start}-{end}" if start != end else str(start))
        lines.append(f"\n### 分布\n\n{'、'.join(ranges)}\n\n")

    # 版本对比（同一 prompt 不同版本）
    by_prompt = {}
    for key, g in groups.items():
        by_prompt.setdefault(g["prompt_name"], []).append(g)
    for pname, versions in sorted(by_prompt.items()):
        if len(versions) < 2:
            continue
        lines.append(f"## {pname} 版本对比\n\n")
        lines.append("| 版本 | 章节数 | 章节范围 |\n|------|-------|---------|\n")
        for v in sorted(versions, key=lambda x: x["version"]):
            chs = v["chapters"]
            lines.append(f"| v{v['version']} | {v['count']} | {min(chs)}-{max(chs)} |\n")
        lines.append("\n")

    Path(compare_dir).mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(lines), encoding="utf-8")
    print(f"  [OK] 版本聚合 → {out_path}")
