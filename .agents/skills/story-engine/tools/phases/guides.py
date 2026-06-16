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

def phase_guides(config, start, end, workers=5, state_mgr=None):
    """生成 plot_guide + style_guide（引用 templates）。"""
    from lib.api_client import get_api_url
    
    guides_dir = f"{config['rewrites_dir']}/guides"

    if state_mgr:
        state_mgr.phase_start("guides")

    # plot-guide（JSON 输出 + 模板合并）
    print(f"\n{'=' * 50}")
    print(f"Phase 2: plot_guide (flash, ch{start}-{end}, 并行)")
    print("=" * 50)

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
            system_prompt=None, extra_replacements=None, retry_context=None):
    """执行单次调用。通过 prompt_loader 加载并嵌入文件内容。
    
    Args:
        retry_context: 重试时附带的修正提示（如"代词密度偏离源文"），注入 system_prompt
    """
    from lib.api_client import get_api_url
    
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("未配置 API_KEY，请设置 $env:API_KEY")

    pc = get_prompt_config_with_overrides(f"{prompt_type}.md", config)
    model = model or pc.get("model", "deepseek-v4-pro")
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

    # 写章时注入文笔指纹 + 角色行为卡片 + 源文段落锚点
    if prompt_type == "write-chapter" and chapter_num:
        from phases.style_extract import load_style_text
        style_md = load_style_text(config, chapter_num)
        replacements["文笔指纹"] = style_md or "（文笔指纹未生成）"
        replacements["角色行为卡片"] = _load_char_card(config)
        # 源文段落锚点（从指纹提取，做硬约束）
        src_text = get_source_text(config, chapter_num)
        if src_text:
            from lib.text_metrics import count_style_fingerprint
            fp = count_style_fingerprint(src_text)
            replacements["源文段长"] = str(int(fp.get("paragraph_avg_len", 40)))
            replacements["源文单句段比例"] = str(int(fp.get("single_sent_ratio", 0.5) * 100))
            replacements["源文对话比"] = str(int(fp.get("dialogue_ratio", 0.1) * 100))
            replacements["源文代词密度"] = str(fp.get("pronoun_density", 15))
            replacements["源文标点"] = fp.get("punct_style", "标点克制")
        else:
            replacements["源文段长"] = "40"; replacements["源文单句段比例"] = "50"
            replacements["源文对话比"] = "10"; replacements["源文代词密度"] = "15"
            replacements["源文标点"] = "标点克制"

    # 写章时按目标字数动态设 max_tokens（够写完整不截断，超字数靠 trim 裁）
    if prompt_type == "write-chapter" and chapter_num:
        src_chars = replacements.get("目标字数", "0")
        try:
            target = int(src_chars)
            multiplier = 2.0 if "pro" in model else 1.6
            max_tokens = max(2048, int(target * multiplier))
        except ValueError:
            max_tokens = pc.get("max_tokens", 8192)
    else:
        max_tokens = pc.get("max_tokens", 8192)

    # 合并额外替换变量
    if extra_replacements:
        replacements.update(extra_replacements)

    prompt_path = f"{prompts_dir}/{prompt_type}.md"
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api", rewrites_dir=config.get("rewrites_dir"))

    if not system_prompt:
        sp_name = get_system_prompt_name(f"{prompt_type}.md") or "system-generic.md"
        system_prompt = load_system_prompt(sp_name) or ""

    # 重试修正提示：注入 system_prompt 前端
    if retry_context:
        system_prompt = f"【修正提示】上一次写这章存在以下问题：{retry_context}。这次务必修正。\n\n{system_prompt}"

    # === Debug: 保存最终发给 API 的完整 prompt ===
    if config.get("debug") and chapter_num and chapter_num <= 3:
        debug_dump_prompt(config, prompt_type, chapter_num, prompt_path, system_prompt, user_prompt, sp_name, pc)

    # prompts_only: 只输出 prompt，不调 API
    if config.get("prompts_only"):
        return f"<!-- PROMPTS_ONLY: {prompt_type} ch{chapter_num} — prompt 已保存至 _debug/ -->"

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
    # 角色变量（优先 book_data.json，fallback 直接从 characters.md 提取）
    book_data = _get_book_data(config.get("rewrites_dir", ""))
    if book_data:
        bd_replacements = make_book_data_replacements(book_data)
        replacements.update(bd_replacements)
    else:
        # Fallback: 直接从 characters.md 提取角色名
        chars_path = Path(config["rewrites_dir"]) / "characters.md"
        if chars_path.exists():
            chars_text = chars_path.read_text(encoding="utf-8")
            for role, key in [("男主", "男主名"), ("女主", "女主名")]:
                m = re.search(rf'{role}[：:]\s*\**(\S+)\**', chars_text)
                if m and key not in replacements:
                    replacements[key] = m.group(1)
    
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

    # prompts_only 跳过模板合并
    if config.get("prompts_only"):
        return result

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


def _load_char_card(config):
    """从 characters.md 读取角色行为卡片，注入写章 prompt。"""
    chars_path = Path(config["rewrites_dir"]) / "settings" / "characters.md"
    if not chars_path.exists():
        return "（角色设定文件不存在）"
    text = chars_path.read_text(encoding="utf-8")
    # 提取行为模式相关内容
    sections = []
    for keyword in ["应激模式", "决策方式", "情感表达", "致命弱点", "行为模式"]:
        idx = text.find(keyword)
        if idx > 0:
            # 往前找角色名
            before = text[:idx].strip().split("\n")[-1]
            sections.append(f"{before.strip()} — {text[idx:idx+200].strip().split(chr(10))[0]}")
    return "\n".join(sections[:8]) if sections else "（角色设定中无行为卡片）"

