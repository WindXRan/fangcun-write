"""Phase 2: Guide 生成（plot_guide + style_guide）
Phase 2.5: Guide 衔接修复"""

import os
import re
import sys
import time
from pathlib import Path

# 添加路径
current_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, current_dir)

from utils import (
    get_total_chapters, count_source_chars, call_api, batch_run
)
from state_manager import atomic_write_text
from prompt_loader import load_prompt


# ============================================================
# Phase 2: Guide 生成
# ============================================================

def phase_guides(config, start, end, workers=5, serial=False, state_mgr=None):
    """生成 plot_guide + style_guide（引用 templates）。"""
    from lib.api_client import get_api_url
    
    guides_dir = f"{config['rewrites_dir']}/guides"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    if state_mgr:
        state_mgr.phase_start("guides")

    # style-guide（引用 templates）
    print(f"\n{'=' * 50}")
    print(f"Phase 2: style_guide (flash, ch{start}-{end}, 引用 templates)")
    print("=" * 50)

    ok_style, fail_style = batch_run(flash, "style-guide", start, end, workers, guides_dir,
                                     "style_{ch}.md", skip_existing=True, state_mgr=state_mgr,
                                     run_one_func=run_one)
    print(f"style_guide: OK={len(ok_style)} FAIL={len(fail_style)}")

    # plot-guide（JSON 输出 + 模板合并）
    print(f"\n{'=' * 50}")
    print(f"Phase 2: plot_guide (flash, ch{start}-{end}, {'串行(质量)' if serial else '并行(速度)'})")
    print("=" * 50)

    if serial:
        prev_summary = ""
        ok, fail = {}, {}
        for ch in range(start, end + 1):
            try:
                overrides = {}
                if prev_summary:
                    overrides["上一章摘要"] = prev_summary
                result = run_one(flash, "plot-guide", ch, extra_replacements=overrides)
                # JSON 输出 + 模板合并
                result = process_plot_guide_output(config, ch, result)
                path = Path(guides_dir) / f"plot_{ch}.md"
                atomic_write_text(path, result)
                ok[ch] = str(path)
                beats = re.findall(r'新书[：:].*?(?=\n|$)', result)
                if not beats:
                    beats = re.findall(r'节拍\d+[：:].*?(?=\n|$)', result)
                prev_summary = '；'.join(beats[-3:]) if beats else result[-300:]
                print(f"  [OK] ch{ch} plot-guide")
            except Exception as e:
                fail[ch] = str(e)
                print(f"  [FAIL] ch{ch}: {e}")
    else:
        ok, fail = batch_run(flash, "plot-guide", start, end, workers, guides_dir,
                             "plot_{ch}.md", skip_existing=True, state_mgr=state_mgr,
                             run_one_func=run_one_with_template)

    print(f"plot_guide: OK={len(ok)} FAIL={len(fail)}")

    if state_mgr:
        if fail or fail_style:
            state_mgr.phase_failed("guides", error=f"plot:{len(fail)} fail, style:{len(fail_style)} fail")
        else:
            state_mgr.phase_done("guides")


def run_one(config, prompt_type, chapter_num=None, model=None, reasoning_effort=None, 
            system_prompt=None, extra_replacements=None):
    """执行单次调用。通过 prompt_loader 加载并嵌入文件内容。"""
    from lib.api_client import get_api_url
    
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY，请设置 $env:API_KEY")

    model = model or config.get("model", "deepseek-v4-flash")
    reasoning_effort = reasoning_effort or config.get("reasoning_effort", "low")
    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    base_dir = config.get("base_dir", os.getcwd())
    api_url = get_api_url(config)

    n = str(chapter_num) if chapter_num else "1"
    n_plus1 = str(chapter_num + 1) if chapter_num else "2"
    total_ch = get_total_chapters(config)
    replacements = {
        "新书名": config["book_name"],
        "N": n,
        "N_plus1": n_plus1,
        "N03d": f"{chapter_num:03d}" if chapter_num else "001",
        "N03d_plus1": f"{chapter_num+1:03d}" if chapter_num else "002",
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
        "总章数": str(total_ch),
    }

    # 需要源文字数时，脚本计算（API 无法跑 PowerShell）
    if prompt_type in ("plot-guide", "style-guide", "write-chapter", "trim-chapter") and chapter_num:
        src_chars = count_source_chars(config, chapter_num)
        target_chars = src_chars  # 1:1对标源文字数
        replacements["源文字数"] = str(src_chars)
        replacements["目标字数"] = str(target_chars)
        replacements["目标字数_min"] = str(int(target_chars * 0.9))
        replacements["目标字数_max"] = str(int(target_chars * 1.1))
    
    # style-guide注入源文指标（从缓存的 style_analysis/style_{N}.json 读取）
    if prompt_type == "style-guide" and chapter_num:
        import json
        style_json = Path(config.get("rewrites_dir", "")).parent / "style_analysis" / f"style_{chapter_num}.json"
        if style_json.exists():
            try:
                metrics = json.loads(style_json.read_text(encoding='utf-8'))
                replacements["源文指标"] = json.dumps(metrics, ensure_ascii=False, indent=2)
            except Exception:
                replacements["源文指标"] = "（JSON读取失败）"
        else:
            replacements["源文指标"] = "（未找到 style_analysis/style_{N}.json，请先运行 --phase style-analysis）"

    max_tokens = 8192  # 不限制，靠重跑兜底

    # 合并额外替换变量（如串行模式的上一章摘要）
    if extra_replacements:
        replacements.update(extra_replacements)

    prompt_path = f"{prompts_dir}/{prompt_type}.md"
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=config.get("rewrites_dir"))

    # 写章时使用每章独立的 style_guide（通过 prompt 中的【style_guide】标签引用）
    sys_prompt = system_prompt or "你是一个专业的网文写手，擅长仿写风格迁移。严格按照提供的指南和指令执行。"

    label = f"ch{chapter_num or '?'} {prompt_type}"
    t_req = time.time()
    try:
        result = call_api(api_key, model, user_prompt, reasoning_effort, max_tokens, sys_prompt, api_url)
        elapsed = time.time() - t_req
        print(f"  [OK] {label} ({elapsed:.0f}s)")
        return result
    except Exception as e:
        elapsed = time.time() - t_req
        print(f"  [FAIL] {label} ({elapsed:.0f}s): {e}")
        raise


def process_plot_guide_output(config, chapter_num, ai_output):
    """处理 plot-guide 的输出，合并到模板。
    
    支持格式：带标签输出（标签：内容）
    
    Args:
        config: 配置字典
        chapter_num: 章节号
        ai_output: AI 输出的文本
    
    Returns:
        合并后的 markdown 文本
    """
    from pathlib import Path
    
    # 获取模板路径
    base_dir = config.get("base_dir", os.getcwd())
    template_path = Path(base_dir) / ".agents/skills/story-engine/templates/plot-guide-output.md"
    
    if not template_path.exists():
        print(f"  [WARN] 模板不存在: {template_path}，使用原始输出")
        return ai_output
    
    try:
        from template_merger import merge_tagged_output
        result = merge_tagged_output(str(template_path), ai_output)
        print(f"  [OK] 标签模板合并完成")
        return result
    except Exception as e:
        print(f"  [WARN] 模板合并失败: {e}，使用原始输出")
        return ai_output


def run_one_with_template(config, prompt_type, chapter_num=None, **kwargs):
    """包装 run_one，自动处理模板合并（用于 plot-guide）。"""
    result = run_one(config, prompt_type, chapter_num, **kwargs)
    
    # 只对 plot-guide 使用模板合并
    if prompt_type == "plot-guide":
        result = process_plot_guide_output(config, chapter_num, result)
    
    return result


# ============================================================
# Phase 2.5: Guide 衔接修复（分批滑动窗口）
# ============================================================

def phase_guide_continuity_fix(config, start, end, batch_size=40):
    """修复 plot_guide 的章间断裂。
    
    分批滑动窗口处理，保证跨章连贯：
    - 首批覆盖 start ~ start+batch_size-1
    - 后续每批步进 batch_size-1（前后各 1 章重叠，防止批间断裂）
    """
    from lib.api_client import get_api_url
    
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        print("[FAIL] 未配置 API_KEY")
        return

    guides_dir = Path(config["rewrites_dir"]) / "guides"
    if not guides_dir.exists():
        print("[FAIL] guides 目录不存在")
        return

    model = config.get("model", "deepseek-v4-flash")
    api_url = get_api_url(config)

    print(f"\n{'=' * 50}")
    print(f"Phase 2.5: Guide 衔接修复 (ch{start}-{end}, batch={batch_size})")
    print("=" * 50)

    total = end - start + 1
    # 滑动窗口计算批次数
    if total <= batch_size:
        batches = [(start, end)]
    else:
        batches = [(start, start + batch_size - 1)]
        cur = start + batch_size - 1
        while cur < end:
            nxt = min(cur + batch_size - 1, end)
            batches.append((cur, nxt))
            cur = nxt

    t0 = time.time()
    for b_idx, (b_start, b_end) in enumerate(batches):
        batch_chs = list(range(b_start, b_end + 1))
        print(f"\n  批 {b_idx+1}/{len(batches)}: 第{b_start}-{b_end}章 ({len(batch_chs)}份guide)")

        # 收集本批所有 plot_guide
        guides = {}
        for ch in batch_chs:
            pf = guides_dir / f"plot_{ch}.md"
            if pf.exists():
                guides[str(ch)] = pf.read_text(encoding='utf-8')

        if not guides:
            print(f"    [SKIP] 无 plot_guide")
            continue

        # 组织 prompt
        parts = ["# Guide 衔接修复\n",
                 "以下为同一部小说的多章章纲（plot_guide），请检查相邻章之间的衔接问题。\n",
                 "## 检查项\n",
                 "1. **角色名一致性**：各章使用的角色名是否完全一致（注意：第一部可能有配角名变化是因为角色正常登场，只要不冲突即可）\n",
                 "2. **人设一致性**：角色的身份、性格、行为模式在跨章时是否连贯\n",
                 "3. **时间线连贯性**：相邻章的时间顺序是否合理，有无跳跃或回溯\n",
                 "4. **场景连续性**：章与章之间的场景转换是否有交代\n",
                 "5. **主线一致性**：各章是否在同一条主线/冲突线上推进，有无另起新线\n",
                 "6. **钩子呼应**：上一章结尾的悬念/约定/未完成事件，下一章是否有回应\n",
                 "\n## 修复要求\n",
                 "- 对**有断裂**的章节，重写其角色列表和节拍映射表中的事件，使其与前后章连贯\n",
                 "- 对**无断裂**的章节，保持原样不动\n",
                 "- **必须保持各章节拍数量、结构功能、情绪曲线与源文的对应关系不变**（这是仿写骨架）\n",
                 "- 只改情节事件、角色名、场景名，不改字数分配、冲突类型标签\n",
                 "- 禁止引入新角色（除非已在本批其他 guide 中出现）\n",
                 "\n## 各章章纲\n"]

        for ch_str in sorted(guides.keys(), key=int):
            parts.append(f"---\n### 第{ch_str}章\n\n{guides[ch_str]}\n")

        parts.append("\n## 输出格式\n")
        parts.append("对每章输出修复后的完整 guide，格式不变。仅对有问题的章做修改，**无问题的章原样输出**。\n")
        parts.append("用分隔符 `===章: N===` 隔开各章输出。\n")

        user_prompt = "".join(parts)

        try:
            result = call_api(api_key, model, user_prompt,
                              reasoning_effort="low", max_tokens=16000,
                              system_prompt="你是专业网文编辑，擅长检查小说章纲的衔接连贯性。只改有问题的部分，不要动没问题的地方。",
                              api_url=api_url)

            # 解析输出
            fixed = 0
            for m in re.finditer(r'===章:\s*(\d+)===', result):
                ch_str = m.group(1)
                start_idx = m.end()
                next_m = re.search(r'===章:\s*\d+===', result[start_idx:])
                content = result[start_idx:start_idx + next_m.start()] if next_m else result[start_idx:]
                content = content.strip()

                out_path = guides_dir / f"plot_{ch_str}.md"
                old_content = out_path.read_text(encoding='utf-8') if out_path.exists() else ""
                if content and content != old_content:
                    out_path.write_text(content, encoding='utf-8')
                    fixed += 1

            elapsed = time.time() - t0
            print(f"    [OK] 修复 {fixed}/{len(guides)} 份 guide ({elapsed:.0f}s)")

        except Exception as e:
            print(f"    [FAIL] 批 {b_idx+1}: {e}")

    print(f"\n[OK] Guide 衔接修复完成 (总耗时 {time.time()-t0:.0f}s)")


def get_source_metrics(config, ch):
    """直接从源文章节计算锚点指标（不依赖 LLM 填写的 style_guide）。"""
    from utils import get_source_text
    from lib.text_metrics import count_metrics
    text = get_source_text(config, ch)
    if text:
        return count_metrics(text)
    return None
