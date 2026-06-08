"""自动迭代优化：对比→评分→分析问题→优化prompt→重跑"""
import os
import sys
import json
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from prompt_loader import load_prompt
from auto_compare import call_api

API_URL = "https://api.deepseek.com/chat/completions"


def score_and_analyze(config, start, end):
    """评分并分析"""
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY")
    
    rewrites_dir = config["rewrites_dir"]
    source_book = config.get("source_book", "")
    author = config.get("author", "")
    base_dir = config.get("base_dir", os.getcwd())
    
    # 读取新书章节
    new_book_text = ""
    for ch in range(start, end + 1):
        ch_file = Path(rewrites_dir) / "chapters" / f"ch_{ch:03d}.txt"
        if ch_file.exists():
            new_book_text += f"\n\n## 新书第{ch}章\n\n{ch_file.read_text(encoding='utf-8')}"
    
    # 读取源文章节
    source_text = ""
    for ch in range(start, end + 1):
        import glob
        patterns = [
            f"projects/{author}/{source_book}/_cache/chapters/第{ch}章*.txt",
            f"projects/{author}/{source_book}/_cache/chapters/第{ch:03d}章*.txt",
        ]
        for pat in patterns:
            for f in sorted(glob.glob(os.path.join(base_dir, pat))):
                source_text += f"\n\n## 源文第{ch}章\n\n{Path(f).read_text(encoding='utf-8')}"
                break
    
    # 构建prompt - 要求JSON格式输出
    user_prompt = f"""请对比以下两份文本，按JSON格式输出评分和分析：

# 版本A（源文）
{source_text[:3000]}...

# 版本B（新书）
{new_book_text[:3000]}...

---

**请严格按以下JSON格式输出，不要加任何其他文字：**

```json
{{
  "quality": 6,
  "plagiarism": 3,
  "style": 5,
  "quality_issue": "质量问题描述",
  "plagiarism_issue": "抄袭问题描述",
  "style_issue": "风格问题描述"
}}
```

评分标准（0-10分，10分最好）：
- quality: 阅读体验、情感铺垫、细节支撑
- plagiarism: 抄袭风险（10=无风险，0=高风险）
- style: 句长、对话比例、叙事节奏匹配度"""
    
    # 调用API
    result = call_api(api_key, "deepseek-v4-flash", user_prompt)
    
    # 解析JSON分数
    import re
    scores = {}
    
    # 尝试提取JSON
    json_match = re.search(r'\{[^{}]*"quality"[^{}]*\}', result, re.DOTALL)
    if json_match:
        try:
            scores = json.loads(json_match.group())
            print(f"    [DEBUG] 解析到JSON: {scores}")
        except json.JSONDecodeError as e:
            print(f"    [WARN] JSON解析失败: {e}")
    
    # 如果JSON解析失败，尝试正则提取
    if not scores:
        print("    [DEBUG] 尝试正则提取...")
        
        # 多种模式匹配
        patterns = [
            (r'quality["\s:]+(\d+)', 'quality'),
            (r'plagiarism["\s:]+(\d+)', 'plagiarism'),
            (r'style["\s:]+(\d+)', 'style'),
            (r'质量分[：:]+\s*(\d+)', 'quality'),
            (r'抄袭风险分[：:]+\s*(\d+)', 'plagiarism'),
            (r'风格分[：:]+\s*(\d+)', 'style'),
        ]
        
        for pattern, key in patterns:
            match = re.search(pattern, result)
            if match:
                scores[key] = int(match.group(1))
                print(f"    [DEBUG] 正则匹配到 {key}: {match.group(1)}")
    
    # 计算总分
    if scores:
        valid_scores = [v for k, v in scores.items() if k in ['quality', 'plagiarism', 'style'] and isinstance(v, int)]
        if valid_scores:
            scores['total'] = round(sum(valid_scores) / len(valid_scores), 1)
    
    return scores, result


def auto_optimize(config, start, end, max_iterations=3):
    """自动迭代优化"""
    print(f"\n{'=' * 50}")
    print(f"自动迭代优化 (ch{start}-{end}, 最多{max_iterations}轮)")
    print("=" * 50)
    
    best_score = 0
    best_iteration = 0
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    
    # 第一轮：先运行pipeline生成章节
    print(f"\n--- 第0轮：生成初始章节 ---")
    print("  [0] 运行pipeline...")
    import subprocess
    cmd = [
        "python", ".agents/skills/story-engine/tools/rewrite_chapters.py",
        "--config", config.get("config_file", "configs/test_new_plot.json"),
        "--start", str(start),
        "--end", str(end),
        "--workers", "3",
        "--phase", "guides,write"
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=600)
    except Exception as e:
        print(f"  [WARN] pipeline运行失败: {e}")
    
    for iteration in range(1, max_iterations + 1):
        print(f"\n--- 第{iteration}轮 ---")
        
        # 1. 评分并分析
        print("  [1] 评分并分析...")
        scores, analysis = score_and_analyze(config, start, end)
        
        print(f"  质量分: {scores.get('quality', '?')}/10")
        print(f"  抄袭风险分: {scores.get('plagiarism', '?')}/10")
        print(f"  风格分: {scores.get('style', '?')}/10")
        print(f"  总分: {scores.get('total', '?')}/10")
        
        # 2. 检查是否达标
        total_score = scores.get('total', 0)
        if total_score >= 7:
            print(f"\n[OK] 达标！总分{total_score}≥7，停止优化")
            return scores, analysis
        
        # 3. 记录最佳
        if total_score > best_score:
            best_score = total_score
            best_iteration = iteration
        
        # 4. 保存分析结果
        compare_dir = Path(config["rewrites_dir"]) / "compare"
        compare_dir.mkdir(exist_ok=True)
        analysis_file = compare_dir / f"optimization_{iteration}.md"
        analysis_file.write_text(f"# 第{iteration}轮优化分析\n\n分数: {scores}\n\n{analysis}", encoding='utf-8')
        
        # 5. 如果是最后一轮，不优化了
        if iteration == max_iterations:
            print(f"\n[END] 达到最大迭代次数，最佳: 第{best_iteration}轮, 总分{best_score}")
            return scores, analysis
        
        # 6. 根据分析自动优化prompt
        print(f"  [2] 根据分析优化prompt...")
        optimize_prompts(analysis, prompts_dir, scores)
        
        # 7. 删除旧章节，重新运行pipeline
        print(f"  [3] 重新运行pipeline...")
        chapters_dir = Path(config["rewrites_dir"]) / "chapters"
        if chapters_dir.exists():
            for f in chapters_dir.glob("ch_*.txt"):
                f.unlink()
        
        guides_dir = Path(config["rewrites_dir"]) / "guides"
        if guides_dir.exists():
            for f in guides_dir.glob("plot_*.md"):
                f.unlink()
            for f in guides_dir.glob("style_*.md"):
                f.unlink()
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=600)
        except Exception as e:
            print(f"  [WARN] pipeline运行失败: {e}")
    
    return scores, analysis


def optimize_prompts(analysis, prompts_dir, scores):
    """根据分析结果自动优化prompt（简化版：只改一处）"""
    import re
    
    # 如果分数为空，跳过优化
    if not scores:
        print("    [SKIP] 分数为空，跳过优化")
        return
    
    # 读取当前plot-guide.md
    plot_guide_path = Path(prompts_dir) / "plot-guide.md"
    if not plot_guide_path.exists():
        print("    [WARN] plot-guide.md不存在，跳过优化")
        return
    
    content = plot_guide_path.read_text(encoding='utf-8')
    
    # 只取数值类型的分数
    numeric_scores = {k: v for k, v in scores.items() if isinstance(v, int) and k in ['quality', 'plagiarism', 'style']}
    
    if not numeric_scores:
        print("    [SKIP] 无数值分数，跳过优化")
        return
    
    # 找出最需要优化的一项
    min_score = min(numeric_scores.values())
    min_key = [k for k, v in numeric_scores.items() if v == min_score][0]
    
    print(f"    [OPTIMIZE] 最弱项: {min_key} ({min_score}/10)")
    
    # 只改一处
    if min_key == 'plagiarism' and min_score < 5:
        # 抄袭风险高：在"核心"部分加强调
        old = "**核心**：只仿骨架（结构+情绪曲线），不仿血肉（具体事件）。情节必须完全不一样。"
        new = "**核心**：只仿骨架（结构+情绪曲线），不仿血肉（具体事件）。**情节必须完全不同，禁止使用相同事件类型。**"
        content = content.replace(old, new)
        print("    [OK] 加强反抄袭强调")
    
    elif min_key == 'style' and min_score < 5:
        # 风格不匹配：在"结构"规则后加一句
        old = "但动作和反应全部换"
        new = "但动作和反应全部换。**句长、对话比例必须接近源文。**"
        content = content.replace(old, new)
        print("    [OK] 加强风格要求")
    
    elif min_key == 'quality' and min_score < 5:
        # 质量差：在"结构"规则后加一句
        old = "但动作和反应全部换"
        new = "但动作和反应全部换。**每个情绪点要有细节支撑，不能只写情绪词。**"
        content = content.replace(old, new)
        print("    [OK] 加强质量要求")
    
    # 保存修改
    plot_guide_path.write_text(content, encoding='utf-8')


if __name__ == "__main__":
    # 测试
    config = {
        "book_name": "斗破苍穹之星辰再起",
        "author": "天蚕土豆",
        "source_book": "斗破苍穹",
        "api_key": os.environ.get("API_KEY"),
        "rewrites_dir": "projects/天蚕土豆/斗破苍穹/rewrites/斗破苍穹之星辰再起",
        "base_dir": "."
    }
    
    scores, analysis = auto_optimize(config, 1, 3, max_iterations=3)
    print(f"\n最终分数: {scores}")
