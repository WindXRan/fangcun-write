"""Phase 2: plot-guide 生成
Phase 2.5: Guide 衔接修复"""

import os
import re
import sys
import time
from pathlib import Path

from utils import (
    get_total_chapters, count_source_chars, call_api, batch_run
)
from state_manager import atomic_write_text
from prompt_loader import load_prompt, load_system_prompt, tag_output, get_prompt_config_with_overrides


# ============================================================
# Phase 2: Guide 生成
# ============================================================

def phase_guides(config, start, end, workers=5, serial=False, state_mgr=None):
    """生成 plot_guide + style_guide（引用 templates）。"""
    from lib.api_client import get_api_url
    
    guides_dir = f"{config['rewrites_dir']}/guides"

    if state_mgr:
        state_mgr.phase_start("guides")

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
                result = run_one(config, "plot-guide", ch, extra_replacements=overrides)
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
        ok, fail = batch_run(config, "plot-guide", start, end, workers, guides_dir,
                             "plot_{ch}.md", skip_existing=True, state_mgr=state_mgr,
                             run_one_func=run_one_with_template)

    print(f"plot_guide: OK={len(ok)} FAIL={len(fail)}")

    if state_mgr:
        if fail:
            state_mgr.phase_failed("guides", error=f"{len(fail)} fail")
        else:
            state_mgr.phase_done("guides")


def run_one(config, prompt_type, chapter_num=None, model=None, reasoning_effort=None, 
            system_prompt=None, extra_replacements=None):
    """执行单次调用。通过 prompt_loader 加载并嵌入文件内容。"""
    from lib.api_client import get_api_url
    
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY，请设置 $env:API_KEY")

    pc = get_prompt_config_with_overrides(f"{prompt_type}.md", config)
    model = model or pc.get("model", "deepseek-v4-flash")
    reasoning_effort = reasoning_effort or pc.get("reasoning_effort", "low")
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
        "genre": config.get("genre", ""),
    }

    # 需要源文字数时，脚本计算（API 无法跑 PowerShell）
    if prompt_type in ("plot-guide", "write-chapter", "trim-chapter") and chapter_num:
        src_chars = count_source_chars(config, chapter_num)
        target_chars = src_chars  # 1:1对标源文字数
        replacements["源文字数"] = str(src_chars)
        replacements["目标字数"] = str(target_chars)
        replacements["目标字数_min"] = str(int(target_chars * 0.9))
        replacements["目标字数_max"] = str(int(target_chars * 1.1))
    
    # plot-guide 和 write-chapter 直接注入源文全文（精度对标，抄袭由下游检测）
    if prompt_type in ("plot-guide", "write-chapter") and chapter_num:
        from utils import get_source_text
        source_text = get_source_text(config, chapter_num)
        if source_text:
            replacements["源文全文"] = source_text
        else:
            replacements["源文全文"] = "（源文读取失败）"

    # 写章时按目标字数动态设 max_tokens（够写完整不截断，超字数靠 trim 裁）
    if prompt_type == "write-chapter" and chapter_num:
        src_chars = replacements.get("目标字数", "0")
        try:
            target = int(src_chars)
            max_tokens = max(2048, int(target * 1.6))
        except ValueError:
            max_tokens = pc.get("max_tokens", 8192)
    else:
        max_tokens = pc.get("max_tokens", 8192)

    # 合并额外替换变量（如串行模式的上一章摘要）
    if extra_replacements:
        replacements.update(extra_replacements)

    prompt_path = f"{prompts_dir}/{prompt_type}.md"
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=config.get("rewrites_dir"))

    if not system_prompt:
        system_prompt = load_system_prompt("system-guide.md")

    label = f"ch{chapter_num or '?'} {prompt_type}"
    t_req = time.time()
    try:
        result = call_api(api_key, model, user_prompt, reasoning_effort, max_tokens, system_prompt, api_url, temperature=pc.get("temperature", 0.8))
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
    合并后自动填充 {N}、{女主名} 等模板变量。
    
    Args:
        config: 配置字典
        chapter_num: 章节号
        ai_output: AI 输出的文本
    
    Returns:
        合并后的 markdown 文本
    """
    from pathlib import Path
    
    base_dir = config.get("base_dir", os.getcwd())
    template_path = Path(base_dir) / ".agents/skills/story-engine/templates/plot-guide-output.md"
    
    if not template_path.exists():
        print(f"  [WARN] 模板不存在: {template_path}，使用原始输出")
        return ai_output
    
    from template_merger import merge_tagged_output, parse_tagged_output, load_template
    template_text = load_template(str(template_path))
    
    # 1. 标签模板合并
    try:
        result = merge_tagged_output(str(template_path), ai_output)
        print(f"  [OK] 标签模板合并完成")
    except Exception as e:
        print(f"  [WARN] 模板合并失败: {e}，使用原始输出")
        return ai_output
    
    # 2. 填充模板中的配置变量（{N}、{源文字数}、{女主名} 等）
    from prompt_loader import make_book_data_replacements
    replacements = {
        "N": str(chapter_num),
        "N03d": f"{chapter_num:03d}",
    }
    # 源文字数 / 目标字数
    from utils import count_source_chars
    src_chars = count_source_chars(config, chapter_num)
    replacements["源文字数"] = str(src_chars)
    replacements["目标字数"] = str(src_chars)
    replacements["目标字数_min"] = str(int(src_chars * 0.9))
    replacements["目标字数_max"] = str(int(src_chars * 1.1))
    # 作者/书名
    replacements["作者名"] = config.get("author", "")
    replacements["新书名"] = config.get("book_name", "")
    replacements["源书名"] = config.get("source_book", "")
    # 角色变量（从 book_data.json）
    book_data = None
    rewrites_dir = config.get("rewrites_dir", "")
    if rewrites_dir:
        bd_path = Path(rewrites_dir) / "book_data.json"
        if bd_path.exists():
            try:
                import json
                book_data = json.loads(bd_path.read_text(encoding="utf-8"))
            except Exception:
                pass
    if book_data:
        bd_replacements = make_book_data_replacements(book_data)
        replacements.update(bd_replacements)
    
    for key, value in replacements.items():
        result = result.replace(f"{{{key}}}", str(value))
    
    # 收集游离标签：AI输出中有但模板没有对应的 → 追加到尾部
    from template_merger import parse_tagged_output
    all_tags = parse_tagged_output(ai_output)
    orphan_sections = []
    for tag, content in all_tags.items():
        placeholder = f"{{{tag}}}"
        if placeholder not in template_text:
            orphan_sections.append(f"## {tag}\n{content}")
    if orphan_sections:
        result += "\n\n" + "\n\n".join(orphan_sections)
    
    return result


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

    pc = get_prompt_config_with_overrides("guide-continuity-fix.md", config)
    model = pc.get("model", config.get("model", "deepseek-v4-flash"))
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

        # 加载 guide-continuity-fix prompt
        prompt_template = load_prompt(
            f"{prompts_dir}/guide-continuity-fix.md",
            base_dir, mode="api",
            rewrites_dir=config.get("rewrites_dir"),
        )
        user_prompt = prompt_template.replace(
            "{guides}",
            '\n'.join(f"---\n### 第{ch_str}章\n\n{guides[ch_str]}\n" for ch_str in sorted(guides.keys(), key=int))
        )

        try:
            result = call_api(api_key, model, user_prompt,
                              reasoning_effort=pc.get("reasoning_effort", "low"),
                              max_tokens=pc.get("max_tokens", 16000),
                              temperature=pc.get("temperature", 0.8),
                              system_prompt=load_system_prompt("system-guide.md"),
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
                    out_path.write_text(tag_output(content, "guide-continuity-fix.md"), encoding='utf-8')
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
