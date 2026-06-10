"""
自动 Prompt 优化器

pipeline 跑完后自动运行：
1. 读取审稿结果（unified_review.json + 审稿报告）
2. 分析问题类型（抄袭/AI痕迹/节奏/人设/时间线等）
3. 提取通用规则
4. 更新对应 prompt（plot-guide / style-guide / write-chapter）
5. 精简冗余规则（prompt 超过600行时自动触发）

用法：
  python auto_prompt_optimize.py --config configs/xxx.json --start 1 --end 10
  python auto_prompt_optimize.py --config configs/xxx.json --mode simplify  # 只精简
  python auto_prompt_optimize.py --config configs/xxx.json --mode expand    # 只扩充
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime


# ============================================================
# 问题分析器
# ============================================================

def load_review_results(rewrites_dir):
    """加载所有审稿结果"""
    results = {
        "unified_review": None,
        "full_review": None,
        "plagiarism_issues": [],
        "ai_marker_issues": [],
        "word_count_issues": [],
        "other_issues": []
    }
    
    compare_dir = Path(rewrites_dir) / "compare"
    if not compare_dir.exists():
        return results
    
    # 加载 unified_review.json
    ur_path = compare_dir / "unified_review.json"
    if ur_path.exists():
        try:
            data = json.loads(ur_path.read_text(encoding="utf-8"))
            results["unified_review"] = data
            
            # 提取问题
            for ch in data.get("chapters", []):
                for issue in ch.get("issues", []):
                    issue_type = issue.get("type", "")
                    entry = {
                        "chapter": ch.get("chapter"),
                        "type": issue_type,
                        "message": issue.get("message", ""),
                        "severity": issue.get("severity", ""),
                        "details": issue.get("details", "")
                    }
                    
                    if issue_type == "plagiarism":
                        results["plagiarism_issues"].append(entry)
                    elif issue_type == "ai_marker":
                        results["ai_marker_issues"].append(entry)
                    elif issue_type == "word_count":
                        results["word_count_issues"].append(entry)
                    else:
                        results["other_issues"].append(entry)
        except Exception:
            pass
    
    # 加载审稿汇总报告
    for f in compare_dir.glob("*汇总*.md"):
        try:
            results["full_review"] = f.read_text(encoding="utf-8")
        except Exception:
            pass
    
    return results


def analyze_issues(results):
    """分析问题，归类为需要 prompt 修复的类别"""
    analysis = {
        "plagiarism": {
            "count": len(results["plagiarism_issues"]),
            "chapters": [i["chapter"] for i in results["plagiarism_issues"]],
            "needs_fix": len(results["plagiarism_issues"]) > 0
        },
        "ai_markers": {
            "count": len(results["ai_marker_issues"]),
            "chapters": [i["chapter"] for i in results["ai_marker_issues"]],
            "needs_fix": len(results["ai_marker_issues"]) > 0,
            "markers": list(set(
                m for i in results["ai_marker_issues"]
                for m in re.findall(r'[「」]([^「」]+)[「」]', i.get("message", ""))
            ))
        },
        "word_count": {
            "count": len(results["word_count_issues"]),
            "chapters": [i["chapter"] for i in results["word_count_issues"]],
            "needs_fix": len(results["word_count_issues"]) > 2
        },
        "narrative": {
            "needs_fix": False,
            "issues": []
        }
    }
    
    # 从审稿汇总报告中提取叙事问题
    review_text = results.get("full_review", "") or ""
    
    # 检测关键词
    narrative_keywords = {
        "时间线": "timeline",
        "人设": "character",
        "漂移": "character_drift",
        "心理转折": "psychological_arc",
        "重复": "repetitive_conflict",
        "钩子": "hook",
        "节奏": "pacing",
        "悬疑": "mystery_pacing"
    }
    
    for keyword, issue_type in narrative_keywords.items():
        if keyword in review_text:
            analysis["narrative"]["needs_fix"] = True
            analysis["narrative"]["issues"].append(issue_type)
    
    return analysis


# ============================================================
# Prompt 修改器
# ============================================================

class PromptOptimizer:
    """Prompt 优化器"""
    
    def __init__(self, prompts_dir):
        self.prompts_dir = Path(prompts_dir)
        self.changes = []
    
    def read_prompt(self, name):
        path = self.prompts_dir / name
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""
    
    def write_prompt(self, name, content):
        path = self.prompts_dir / name
        path.write_text(content, encoding="utf-8")
        self.changes.append(f"Updated {name}")
    
    def optimize_for_plagiarism(self):
        """加强反抄袭规则"""
        content = self.read_prompt("plot-guide.md")
        if not content:
            return
        
        # 检查是否已有足够的反抄袭规则
        if "8-gram" in content and "台词比对" in content:
            # 规则已存在，加强措辞
            old = "**核心**：只仿骨架（结构+情绪曲线），不仿血肉（具体事件）。情节必须完全不一样。"
            new = "**核心**：只仿骨架（结构+情绪曲线），不仿血肉（具体事件）。情节必须完全不一样。\n\n**⚠️ 抄袭红线**：连续8字以上与源文重合 = 抄袭。写完后逐句检查台词，确保无任何6字以上连续匹配。"
            if old in content and "抄袭红线" not in content:
                content = content.replace(old, new)
                self.write_prompt("plot-guide.md", content)
                print("  [OPT] 加强反抄袭红线提示")
        else:
            print("  [SKIP] 反抄袭规则已足够")
    
    def optimize_for_ai_markers(self, markers=None):
        """加强 AI 路标词过滤"""
        content = self.read_prompt("style-guide.md")
        if not content:
            return
        
        # 检查是否已有完整清单
        if "AI路标词完整禁用清单" in content:
            # 如果有新发现的 AI 词，追加到清单
            if markers:
                existing_markers = set(re.findall(r'[^\s,，、]+', content))
                new_markers = [m for m in markers if m not in existing_markers]
                if new_markers:
                    # 追加到"句中禁用"部分
                    insert_point = content.find("**直抒情禁用**")
                    if insert_point > 0:
                        additions = "\n".join(f"- {m}" for m in new_markers)
                        content = content[:insert_point] + additions + "\n\n" + content[insert_point:]
                        self.write_prompt("style-guide.md", content)
                        print(f"  [OPT] 追加 {len(new_markers)} 个新 AI 路标词")
            print("  [SKIP] AI 路标词规则已足够")
            return
        
        print("  [SKIP] 需要手动添加 AI 路标词清单")
    
    def optimize_for_narrative(self, issues):
        """根据审稿反馈优化叙事规则"""
        plot_guide = self.read_prompt("plot-guide.md")
        write_chapter = self.read_prompt("write-chapter.md")
        
        if not plot_guide or not write_chapter:
            return
        
        for issue in issues:
            if issue == "timeline" and "时间线过渡规则" not in plot_guide:
                print("  [OPT] 需要添加时间线过渡规则（请手动或使用 --mode expand）")
            
            if issue == "character_drift" and "角色心理弧线追踪" not in plot_guide:
                print("  [OPT] 需要添加角色心理弧线追踪（请手动或使用 --mode expand）")
            
            if issue == "repetitive_conflict" and "冲突升级规则" not in plot_guide:
                print("  [OPT] 需要添加冲突升级规则（请手动或使用 --mode expand）")
            
            if issue == "psychological_arc" and "角色心理锚点" not in write_chapter:
                print("  [OPT] 需要添加角色心理锚点（请手动或使用 --mode expand）")
    
    def simplify(self, max_lines=600):
        """精简 prompt：去除重复规则、合并相似项"""
        for name in ["plot-guide.md", "style-guide.md", "write-chapter.md"]:
            content = self.read_prompt(name)
            if not content:
                continue
            
            lines = content.split("\n")
            if len(lines) <= max_lines:
                print(f"  [SIMPLIFY] {name}: {len(lines)}行，无需精简")
                continue
            
            print(f"  [SIMPLIFY] {name}: {len(lines)}行 → 开始精简...")
            
            # 1. 去除连续空行（保留最多1个）
            new_lines = []
            prev_empty = False
            for line in lines:
                is_empty = line.strip() == ""
                if is_empty and prev_empty:
                    continue
                new_lines.append(line)
                prev_empty = is_empty
            
            # 2. 合并重复的规则标题
            seen_headers = set()
            final_lines = []
            for line in new_lines:
                if line.startswith("## ") or line.startswith("### "):
                    if line in seen_headers:
                        continue
                    seen_headers.add(line)
                final_lines.append(line)
            
            # 3. 去除过多的示例（每种规则最多保留2个正例+2个反例）
            # 这个比较复杂，先跳过，留给手动精简
            
            if len(final_lines) < len(lines):
                self.write_prompt(name, "\n".join(final_lines))
                print(f"  [SIMPLIFY] {name}: {len(lines)}行 → {len(final_lines)}行")
            else:
                print(f"  [SIMPLIFY] {name}: 无变化")


# ============================================================
# 主流程
# ============================================================

def run_optimize(config, start, end, mode="auto"):
    """运行 prompt 优化"""
    rewrites_dir = config["rewrites_dir"]
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    
    print(f"\n{'=' * 50}")
    print(f"Prompt 优化 | mode={mode}")
    print(f"{'=' * 50}")
    
    optimizer = PromptOptimizer(prompts_dir)
    
    if mode == "simplify":
        print("\n--- 精简模式 ---")
        optimizer.simplify()
        return optimizer.changes
    
    if mode == "expand":
        print("\n--- 扩充模式 ---")
        # 扩充需要审稿结果
        results = load_review_results(rewrites_dir)
        analysis = analyze_issues(results)
        optimizer.optimize_for_narrative(analysis["narrative"]["issues"])
        return optimizer.changes
    
    # auto 模式：分析→优化→精简
    print("\n--- 加载审稿结果 ---")
    results = load_review_results(rewrites_dir)
    
    if not results["unified_review"] and not results["full_review"]:
        print("  未找到审稿结果，跳过优化")
        return []
    
    analysis = analyze_issues(results)
    
    print(f"\n--- 分析结果 ---")
    print(f"  抄袭问题: {analysis['plagiarism']['count']}章")
    print(f"  AI痕迹: {analysis['ai_markers']['count']}章")
    print(f"  字数偏差: {analysis['word_count']['count']}章")
    print(f"  叙事问题: {analysis['narrative']['issues']}")
    
    print(f"\n--- 优化 Prompt ---")
    
    # 1. 抄袭相关
    if analysis["plagiarism"]["needs_fix"]:
        optimizer.optimize_for_plagiarism()
    
    # 2. AI痕迹相关
    if analysis["ai_markers"]["needs_fix"]:
        optimizer.optimize_for_ai_markers(analysis["ai_markers"].get("markers"))
    
    # 3. 叙事相关
    if analysis["narrative"]["needs_fix"]:
        optimizer.optimize_for_narrative(analysis["narrative"]["issues"])
    
    # 4. 自动精简（超过600行时）
    optimizer.simplify()
    
    # 保存优化记录
    log_path = Path(rewrites_dir) / "compare" / "prompt_optimize_log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "chapters": f"{start}-{end}",
        "analysis": {k: v for k, v in analysis.items() if isinstance(v, dict) and "count" in v},
        "changes": optimizer.changes
    }
    
    # 追加到日志
    log_data = []
    if log_path.exists():
        try:
            log_data = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            log_data = []
    log_data.append(log_entry)
    log_path.write_text(json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"\n--- 完成 ---")
    print(f"  变更: {optimizer.changes}")
    print(f"  日志: {log_path}")
    
    return optimizer.changes


def main():
    parser = argparse.ArgumentParser(description="自动 Prompt 优化器")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=999)
    parser.add_argument("--mode", choices=["auto", "simplify", "expand"], default="auto",
                        help="auto=分析+优化+精简 | simplify=只精简 | expand=只扩充")
    args = parser.parse_args()
    
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)
    
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("prompts_dir", ".agents/skills/story-engine/prompts")
    config.setdefault("base_dir", os.getcwd())
    
    changes = run_optimize(config, args.start, args.end, args.mode)
    
    if changes:
        print(f"\n优化完成，共 {len(changes)} 项变更")
    else:
        print(f"\n无需优化")


if __name__ == "__main__":
    main()
