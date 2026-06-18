"""Phase 2: plot-guide 生成"""

import os
import re
import time
from pathlib import Path

from utils import (
    get_total_chapters, count_source_chars, batch_run, debug_dump_prompt,
    get_source_text
)
from prompt_meta import load_system_prompt, get_prompt_config_with_overrides, get_system_prompt_name, safe_format
from prompt_loader import load_prompt

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


def _extract_highlights(src_text, max_chars=300):
    """从源文提取情绪密度最高的段落作为参考。"""
    if not src_text:
        return ""
    
    # 按段落分割
    paragraphs = [p.strip() for p in src_text.split('\n') if p.strip() and len(p.strip()) > 20]
    if not paragraphs:
        return ""
    
    # 情绪关键词权重
    emotion_words = {
        '哭': 3, '泪': 3, '怕': 2, '紧': 2, '慌': 2, '急': 2, '抖': 2,
        '死': 3, '命': 2, '血': 3, '痛': 2, '苦': 2, '惨': 2,
        '笑': 1, '喜': 1, '乐': 1, '甜': 1, '暖': 1,
        '怒': 2, '恨': 2, '骂': 2, '打': 2, '摔': 2,
        '空': 2, '饿': 2, '冷': 2, '黑': 1, '暗': 1,
    }
    
    # 计算每段的情绪分数
    scored = []
    for p in paragraphs:
        score = sum(emotion_words.get(w, 0) for w in p if w in emotion_words)
        # 对话加分（有引号）
        if '"' in p or '"' in p or '「' in p:
            score += 2
        # 短句加分（节奏感）
        short_sents = len([s for s in p.split('。') if 0 < len(s) < 20])
        score += short_sents
        scored.append((score, p))
    
    # 按分数排序，取前几段
    scored.sort(key=lambda x: x[0], reverse=True)
    
    result = []
    total = 0
    for score, p in scored:
        if total + len(p) > max_chars:
            break
        result.append(p)
        total += len(p)
    
    return '\n\n'.join(result[:3])  # 最多3段


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
    from lib.api_client import call_llm, get_api_url

    prompts_dir = config.get("prompts_dir", ".agents/skills/story-engine/prompts")
    base_dir = config.get("base_dir", os.getcwd())

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
    if prompt_type in ("plot-guide", "write-chapter", "trim-chapter") and chapter_num:
        src_chars = count_source_chars(config, chapter_num)
        target_chars = src_chars if src_chars > 0 else 1500  # 源文缺失则用默认值
        replacements["源文字数"] = str(src_chars)
        replacements["目标字数"] = str(target_chars)
        replacements["目标字数_min"] = str(int(target_chars * 0.9))
        replacements["目标字数_max"] = str(int(target_chars * 1.1))
    
    # plot-guide 注入源文（供 LLM 分析结构/情绪/节奏，不注入给 write-chapter）
    if prompt_type == "plot-guide" and chapter_num:
        source_text = get_source_text(config, chapter_num)
        replacements["源文全文"] = source_text or "（源文读取失败）"
        # 注入角色名（plot-guide 也需要，否则角色名会乱）
        book_data = _get_book_data(config.get("rewrites_dir", ""))
        if book_data:
            from prompt_loader import make_book_data_replacements
            bd_replacements = make_book_data_replacements(book_data)
            for k, v in bd_replacements.items():
                if k not in replacements:
                    replacements[k] = v
        if "女主名" not in replacements or "男主名" not in replacements:
            chars_path = Path(config["rewrites_dir"]) / "characters.md"
            if chars_path.exists():
                chars_text = chars_path.read_text(encoding="utf-8")
                for role, key in [("女主", "女主名"), ("男主", "男主名"), ("主角", "女主名")]:
                    if key not in replacements:
                        m = re.search(rf'{role}[：:]\s*\**(\S+)\**', chars_text)
                        if m:
                            replacements[key] = m.group(1)
        # 注入世界观（plot-guide 和 write-chapter 都需要）
        if "世界观" not in replacements:
            world_path = Path(config["rewrites_dir"]) / "world.md"
            if world_path.exists():
                replacements["世界观"] = world_path.read_text(encoding="utf-8")[:2000]
            else:
                replacements["世界观"] = "（世界观文件不存在，请参考源文设定）"

    # 写章时注入源文段落锚点
    if prompt_type == "write-chapter" and chapter_num:
        # 注入角色名（女主名、男主名等）
        book_data = _get_book_data(config.get("rewrites_dir", ""))
        if book_data:
            from prompt_loader import make_book_data_replacements
            bd_replacements = make_book_data_replacements(book_data)
            for k, v in bd_replacements.items():
                if k not in replacements:
                    replacements[k] = v
        # Fallback: 直接从 characters.md 提取
        if "女主名" not in replacements or "男主名" not in replacements:
            chars_path = Path(config["rewrites_dir"]) / "characters.md"
            if chars_path.exists():
                chars_text = chars_path.read_text(encoding="utf-8")
                for role, key in [("女主", "女主名"), ("男主", "男主名")]:
                    if key not in replacements:
                        m = re.search(rf'{role}[：:]\s*\**(\S+)\**', chars_text)
                        if m:
                            replacements[key] = m.group(1)
        # 注入世界观
        if "世界观" not in replacements:
            world_path = Path(config["rewrites_dir"]) / "world.md"
            if world_path.exists():
                replacements["世界观"] = world_path.read_text(encoding="utf-8")[:2000]
            else:
                replacements["世界观"] = "（世界观文件不存在，请参考源文设定）"
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
            replacements["源文高光"] = ""

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

    pc = get_prompt_config_with_overrides(f"{prompt_type}.md", config)

    # === Debug: 保存最终发给 API 的完整 prompt ===
    if config.get("debug") and chapter_num and chapter_num <= 3:
        debug_dump_prompt(config, prompt_type, chapter_num, prompt_path, system_prompt, user_prompt, sp_name, pc)

    # prompts_only: 只输出 prompt，不调 API
    if config.get("prompts_only"):
        return f"<!-- PROMPTS_ONLY: {prompt_type} ch{chapter_num} — prompt 已保存至 _debug/ -->"

    label = f"ch{chapter_num or '?'} {prompt_type}"

    t_req = time.time()
    try:
        result = call_llm(config, prompt_type, user_prompt, system_prompt, ch=chapter_num)
        elapsed = time.time() - t_req
        print(f"  [OK] {label} ({elapsed:.0f}s)")
        return result
    except Exception as e:
        elapsed = time.time() - t_req
        print(f"  [FAIL] {label} ({elapsed:.0f}s): {e}")
        raise


def process_plot_guide_output(config, chapter_num, ai_output):
    """处理 plot-guide 的输出，填充剩余模板变量。
    
    AI 已在 prompt 中直接输出完整 markdown（模板内嵌），
    这里只做 {N}、{女主名} 等变量的补替换。
    """
    from pathlib import Path
    from prompt_loader import make_book_data_replacements

    result = ai_output

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
    book_data = _get_book_data(config.get("rewrites_dir", ""))
    if book_data:
        bd_replacements = make_book_data_replacements(book_data)
        replacements.update(bd_replacements)
    else:
        chars_path = Path(config["rewrites_dir"]) / "characters.md"
        if chars_path.exists():
            chars_text = chars_path.read_text(encoding="utf-8")
            for role, key in [("男主", "男主名"), ("女主", "女主名")]:
                m = re.search(rf'{role}[：:]\s*\**(\S+)\**', chars_text)
                if m and key not in replacements:
                    replacements[key] = m.group(1)

    result = safe_format(result, replacements)

    # 事后校验：如果还有 {xxx} 占位符残留，告警但不阻塞
    remaining = re.findall(r'\{[a-zA-Z\u4e00-\u9fa5]+\}', result)
    if remaining:
        print(f"  [WARN] 以下模板变量未填充: {set(remaining)}")

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
    rewrites_dir = Path(config["rewrites_dir"])
    # 优先 settings/ 目录，fallback 到 rewrites_dir 根目录
    chars_path = rewrites_dir / "settings" / "characters.md"
    if not chars_path.exists():
        chars_path = rewrites_dir / "characters.md"
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

