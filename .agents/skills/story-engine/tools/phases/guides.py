"""Phase 2: plot-guide 生成"""

import os
import re
import time
from pathlib import Path

from utils import (
    get_total_chapters, count_source_chars, call_api, batch_run, debug_dump_prompt,
    get_source_text
)
from prompt_loader import load_prompt, load_system_prompt, get_prompt_config_with_overrides, get_system_prompt_name

# 模块级缓存：book_data.json 每章都读，缓存一次
_book_data_cache = None


def _get_book_data(rewrites_dir):
    """读取 book_data.json（模块级缓存）。"""
    global _book_data_cache
    if _book_data_cache is not None:
        return _book_data_cache
    if rewrites_dir:
        bd_path = Path(rewrites_dir) / "book_data.json"
        if bd_path.exists():
            import json
            try:
                _book_data_cache = json.loads(bd_path.read_text(encoding="utf-8"))
            except Exception:
                _book_data_cache = {}
            return _book_data_cache
    _book_data_cache = {}
    return _book_data_cache


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
        target_chars = src_chars if src_chars > 0 else 1500  # 源文缺失则用默认值
        replacements["源文字数"] = str(src_chars)
        replacements["目标字数"] = str(target_chars)
        replacements["目标字数_min"] = str(int(target_chars * 0.9))
        replacements["目标字数_max"] = str(int(target_chars * 1.1))
    
    # plot-guide 注入脱敏版源文（防数据泄漏，但仍保留结构/节奏参考）
    # write-chapter 不注入源文全文：writer 只通过 plot_guide 了解结构，防止按源文 paraphrase
    if prompt_type == "plot-guide" and chapter_num:
        from lib.source_stripper import strip_source_chapter
        stripped = strip_source_chapter(config, chapter_num)
        if stripped:
            replacements["源文全文"] = stripped
        else:
            source_text = get_source_text(config, chapter_num)
            replacements["源文全文"] = source_text or "（源文读取失败）"

    # 写章时注入文笔指纹：算法锚点（即时算）+ LLM分析（缓存）
    if prompt_type == "write-chapter" and chapter_num:
        from lib.text_metrics import count_style_fingerprint, format_style_anchors
        src_text = get_source_text(config, chapter_num)
        if src_text:
            fp = count_style_fingerprint(src_text)
            replacements["文笔锚点"] = format_style_anchors(fp)
            replacements["文笔风格"] = _get_style_analysis(config, chapter_num, src_text, fp, api_key, api_url, model)
        else:
            replacements["文笔锚点"] = "（无源文）"
            replacements["文笔风格"] = "（无源文）"

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
        sp_name = get_system_prompt_name(f"{prompt_type}.md") or "system-guide.md"
        system_prompt = load_system_prompt(sp_name)

    # === Debug: 保存最终发给 API 的完整 prompt ===
    if config.get("debug"):
        # 非写章阶段只保留第 1 章样本, 写章阶段保留前 3 章
        if prompt_type == "write-chapter":
            if chapter_num and chapter_num <= 3:
                debug_dump_prompt(config, prompt_type, chapter_num, prompt_path, system_prompt, user_prompt, sp_name, pc)
        elif chapter_num == 1 or chapter_num is None:
            debug_dump_prompt(config, prompt_type, chapter_num, prompt_path, system_prompt, user_prompt, sp_name, pc)

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
    src_chars = count_source_chars(config, chapter_num)
    replacements = {
        "N": str(chapter_num),
        "N03d": f"{chapter_num:03d}",
        "源文字数": str(src_chars),
        "目标字数": str(src_chars),
        "目标字数_min": str(int(src_chars * 0.9)),
        "目标字数_max": str(int(src_chars * 1.1)),
        "作者名": config.get("author", ""),
        "新书名": config.get("book_name", ""),
        "源书名": config.get("source_book", ""),
    }
    # 角色变量（从 book_data.json，缓存读）
    book_data = _get_book_data(config.get("rewrites_dir", ""))
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





def get_source_metrics(config, ch):
    """直接从源文章节计算锚点指标（不依赖 LLM 填写的 style_guide）。"""
    from utils import get_source_text
    from lib.text_metrics import count_metrics
    text = get_source_text(config, ch)
    if text:
        return count_metrics(text)
    return None


def _get_style_analysis(config, ch, src_text, algo_fp, api_key, api_url, model):
    """获取 LLM 风格分析（写章时内联调用，结果缓存到 style_{N}.json）。"""
    import json, requests
    from pathlib import Path
    from prompt_loader import load_prompt_str, get_prompt_config_with_overrides

    style_file = Path(config["rewrites_dir"]) / "styles" / f"style_{ch:03d}.json"

    # 命中缓存
    if style_file.exists():
        try:
            data = json.loads(style_file.read_text(encoding="utf-8"))
            if data.get("llm_analysis"):
                return data["llm_analysis"]
        except Exception:
            pass

    # 无 API key，跳过 LLM
    if not api_key:
        return "（无API_KEY，跳过）"

    prompt_template = load_prompt_str("style-analyze.md")
    if not prompt_template:
        return "（prompt 缺失）"

    from lib.text_metrics import format_style_anchors
    prompt = prompt_template.format(
        chapter_text=src_text[:3000],
        style_anchors=format_style_anchors(algo_fp),
    )

    pc = get_prompt_config_with_overrides("style-analyze.md", config)
    try:
        resp = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": pc.get("model", model),
                "messages": [
                    {"role": "system", "content": "你是资深文学编辑。分析文笔风格，3-5句话即可。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": pc.get("temperature", 0.3),
                "max_tokens": pc.get("max_tokens", 1024),
            },
            timeout=60,
        )
        if resp.status_code == 200:
            analysis = resp.json()["choices"][0]["message"]["content"].strip()
            style_file.parent.mkdir(parents=True, exist_ok=True)
            style_file.write_text(json.dumps(
                {"algo": algo_fp, "llm_analysis": analysis},
                ensure_ascii=False, indent=2,
            ), encoding="utf-8")
            print(f"  [STYLE] ch{ch:03d}")
            return analysis
    except Exception as e:
        print(f"  [STYLE] ch{ch:03d} err: {e}")

    return "（LLM分析失败）"
