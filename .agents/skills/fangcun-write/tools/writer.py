"""
fangcun-write: 通用写章模块

完整流程：写章 → dispatch_fix（trim/expand/polish） → validate → 不通过则重试

核心：调用 fangcun-novel 的 run_one() 处理 prompt 加载、变量注入、文件嵌入。
不重复造轮子。
"""

import os
import re
import json
from pathlib import Path


def _setup_imports():
    """设置导入路径"""
    import sys
    analyze_tools = Path(__file__).parent.parent.parent / "fangcun-analyze" / "tools"
    novel_tools = Path(__file__).parent.parent.parent / "fangcun-novel" / "tools"
    for d in [str(analyze_tools), str(novel_tools)]:
        if d not in sys.path:
            sys.path.insert(0, d)
    from lib.api_client import call_llm
    from prompt_meta import safe_format, load_system_prompt
    from phases.guides import run_one
    from utils import get_source_text, count_source_chars
    from file_io import load_style_text
    from lib.text_metrics import count_metrics
    return call_llm, safe_format, load_system_prompt, run_one, get_source_text, count_source_chars, load_style_text, count_metrics


def get_writer_dirs(config):
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    return {
        "rewrites_dir": rewrites_dir,
        "chapters_dir": rewrites_dir / "chapters",
        "guides_dir": rewrites_dir / "guides",
        "analysis_dir": rewrites_dir / "analysis",
    }

def _load_fanfic_config(config):
    """加载同人配置"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from fanfic_config import FanficConfig, CharacterVoice
    
    fanfic_cfg = FanficConfig()
    fanfic_cfg.mode = config.get("fanfic_mode", "canon")
    
    # 加载正典参照
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    canon_candidates = [
        rewrites_dir / "fanfic_canon.md",
        rewrites_dir / "analysis" / "fanfic_canon.md",
        rewrites_dir / "canon.md",
    ]
    for path in canon_candidates:
        if path.exists():
            fanfic_cfg.fanfic_canon = path.read_text(encoding="utf-8")
            break
    
    # 加载角色语音档案
    voice_candidates = [
        rewrites_dir / "character_voices.json",
        rewrites_dir / "analysis" / "character_voices.json",
    ]
    for path in voice_candidates:
        if path.exists():
            try:
                voices_data = json.loads(path.read_text(encoding="utf-8"))
                for name, voice_dict in voices_data.items():
                    fanfic_cfg.character_voices[name] = CharacterVoice(
                        name=name,
                        catchphrases=voice_dict.get("catchphrases", []),
                        speaking_style=voice_dict.get("speaking_style", ""),
                        typical_behavior=voice_dict.get("typical_behavior", ""),
                        forbidden_phrases=voice_dict.get("forbidden_phrases", []),
                    )
            except Exception:
                pass
            break
    
    # 加载伏笔账本
    hook_candidates = [
        rewrites_dir / "hook_ledger.json",
        rewrites_dir / "analysis" / "hook_ledger.json",
    ]
    for path in hook_candidates:
        if path.exists():
            try:
                from fanfic_config import HookEntry
                hooks_data = json.loads(path.read_text(encoding="utf-8"))
                for hook_dict in hooks_data:
                    fanfic_cfg.hook_ledger.append(HookEntry(
                        hook_id=hook_dict.get("hook_id", ""),
                        description=hook_dict.get("description", ""),
                        planted_chapter=hook_dict.get("planted_chapter", 0),
                        seed_text=hook_dict.get("seed_text", ""),
                        status=hook_dict.get("status", "planted"),
                        resolve_chapter=hook_dict.get("resolve_chapter"),
                    ))
            except Exception:
                pass
            break
    
    return fanfic_cfg


def _load_memory_db(config):
    """加载记忆数据库"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from memory_db import MemoryDB
    
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    memory_path = rewrites_dir / "memory_db.json"
    
    return MemoryDB.load(str(memory_path))


def _save_memory_db(config, memory_db):
    """保存记忆数据库"""
    rewrites_dir = Path(config.get("rewrites_dir", ""))
    memory_path = rewrites_dir / "memory_db.json"
    memory_db.save(str(memory_path))




def _get_text_chars(text):
    return len(re.sub(r'\s', '', text))


# ============================================================
# 核心：用 run_one 执行所有 LLM 调用
# ============================================================

def write_chapter(config, ch_num, mode="imitation", context=None, auto_fix=True, max_retries=2):
    """写单章：写章 → dispatch_fix → validate → 不通过则重试。
    
    直接调用 fangcun-novel 的 run_one()，不自己加载 prompt。
    """
    imports = _setup_imports()
    call_llm, safe_format, load_system_prompt, run_one, get_source_text, count_source_chars, load_style_text, count_metrics = imports
    
    fix_config = {**config, "_current_ch_num": ch_num}
    last_issues = []
    system_prompt = load_system_prompt("system-generic.md") or ""
    
    for attempt in range(max_retries + 1):
        try:
            extra = {}
            if context:
                extra["context"] = context
            if attempt > 0:
                extra["失败原因"] = "\n".join(last_issues)
                extra["retry_context"] = "\n".join(last_issues)
            
            result = run_one(
                config, "write-chapter", ch_num,
                extra_replacements=extra if extra else None,
                retry_context="\n".join(last_issues) if attempt > 0 and last_issues else None
            )
        except Exception as e:
            print(f"    [ERROR] ch{ch_num:03d} 写章失败: {e}")
            return None
        
        if not result:
            return None
        
        # dispatch_fix（trim/expand/polish）
        if auto_fix:
            result = _dispatch_fix(fix_config, ch_num, result, mode)
        
        # validate
        passed, issues = _validate_chapter(config, ch_num, result, mode)
        
        if passed:
            if attempt > 0:
                print(f"    [OK] ch{ch_num:03d} 重试第{attempt}次通过验证")
            return result
        
        last_issues = issues
        if attempt < max_retries:
            print(f"    [RETRY] ch{ch_num:03d} 验证不通过 ({', '.join(issues[:2])})，重试 {attempt+1}/{max_retries}")
        else:
            print(f"    [WARN] ch{ch_num:03d} 重试{max_retries}次仍不通过: {', '.join(issues[:2])}")
            return result


# ============================================================
# Post-processing: dispatch_fix + validate
# ============================================================

def _dispatch_fix(config, ch_num, text, mode):
    """写后修复：按问题类型派发 trim/expand/polish，每章必 polish。"""
    imports = _setup_imports()
    call_llm, safe_format, load_system_prompt, run_one, get_source_text, count_source_chars, load_style_text, count_metrics = imports
    
    chars = _get_text_chars(text)
    source_text = get_source_text(config, ch_num) if mode == "imitation" else None
    src_metrics = count_metrics(source_text) if source_text else None
    our_metrics = count_metrics(text)
    
    # 字数超标 → trim
    if chars > 3000:
        print(f"    [FIX] ch{ch_num:03d} 字数超标 {chars} → trim")
        result = _do_trim(config, ch_num, text, mode)
        if result:
            text = result
            chars = _get_text_chars(text)
            our_metrics = count_metrics(text)
    
    # 字数不足 → expand
    elif chars < 2000:
        print(f"    [FIX] ch{ch_num:03d} 字数不足 {chars} → expand")
        result = _do_expand(config, ch_num, text, mode)
        if result:
            text = result
            chars = _get_text_chars(text)
            our_metrics = count_metrics(text)
    
    # 检查是否需要 polish
    polish_reason = None
    if src_metrics:
        limit = max(src_metrics.get("ai_markers", 0) + 1, 1)
        if our_metrics.get("ai_markers", 0) > limit:
            polish_reason = f"AI路标词 {our_metrics['ai_markers']}处 (源文{src_metrics['ai_markers']})"
        if not polish_reason and src_metrics.get("pronoun_density", 0) > 0:
            ratio = our_metrics["pronoun_density"] / max(src_metrics["pronoun_density"], 0.001)
            if ratio > 1.5 or ratio < 0.5:
                polish_reason = f"代词密度偏离 {ratio:.1f}x"
        if not polish_reason and src_metrics.get("sent_len_stddev", 0) > 0:
            ratio = our_metrics["sent_len_stddev"] / max(src_metrics["sent_len_stddev"], 0.001)
            if ratio > 1.5 or ratio < 0.5:
                polish_reason = f"句长偏离 {ratio:.1f}x"
    
    if not polish_reason:
        polish_reason = "风格对齐"
    
    print(f"    [POLISH] ch{ch_num:03d} ({polish_reason})")
    result = _do_polish(config, ch_num, text, mode, polish_reason)
    if result:
        text = result
    
    return text


def _do_trim(config, ch_num, text, mode):
    """执行 trim（用 run_one）"""
    imports = _setup_imports()
    run_one = imports[3]
    chars = _get_text_chars(text)
    target_chars = int(config.get("source_chars", 2500))
    need_cut = chars - target_chars
    try:
        result = run_one(config, "trim-chapter", ch_num, extra_replacements={
            "content": text,
            "当前字数": str(chars),
            "需删减": str(need_cut),
        })
        if result:
            result_chars = _get_text_chars(result)
            if result_chars < target_chars * 0.8 or result_chars > chars * 0.95:
                print(f"    [WARN] trim 结果异常 ({result_chars}/{target_chars})，跳过")
                return None
        return result
    except Exception as e:
        print(f"    [WARN] trim 失败: {e}")
        return None


def _do_expand(config, ch_num, text, mode):
    """执行 expand（用 run_one）"""
    imports = _setup_imports()
    run_one = imports[3]
    chars = _get_text_chars(text)
    try:
        result = run_one(config, "expand-chapter", ch_num, extra_replacements={
            "content": text,
        })
        if result:
            result_chars = _get_text_chars(result)
            target_chars = int(config.get("source_chars", 2500))
            if result_chars > target_chars * 1.3:
                print(f"    [WARN] expand 加太多 ({result_chars}/{target_chars})，跳过")
                return None
        return result
    except Exception as e:
        print(f"    [WARN] expand 失败: {e}")
        return None


def _do_polish(config, ch_num, text, mode, reason=""):
    """执行 polish（用 run_one）"""
    imports = _setup_imports()
    run_one = imports[3]
    source_text = imports[4](config, ch_num) if mode == "imitation" else None
    chars = _get_text_chars(text)
    try:
        result = run_one(config, "polish-chapter", ch_num, extra_replacements={
            "content": text,
            "source_text": source_text or "（无源文，通用润色）",
            "min_chars": str(int(chars * 0.9)),
            "max_chars": str(int(chars * 1.1)),
        })
        return result
    except Exception as e:
        print(f"    [WARN] polish 失败: {e}")
        return None


def _validate_chapter(config, ch_num, text, mode):
    """验证单章质量。返回 (pass: bool, issues: list)。"""
    imports = _setup_imports()
    count_metrics = imports[7]
    get_source_text = imports[4]
    
    issues = []
    our_metrics = count_metrics(text)
    source_text = get_source_text(config, ch_num) if mode == "imitation" else None
    src_metrics = count_metrics(source_text) if source_text else None
    
    chars = _get_text_chars(text)
    target = int(config.get("source_chars", 2500))
    
    if target > 0:
        deviation = (chars - target) / target
        if deviation > 0.15:
            issues.append(f"字数超标 {chars}/{target} (+{deviation:.0%})")
        elif deviation < -0.15:
            issues.append(f"字数不足 {chars}/{target} ({deviation:.0%})")
    
    if src_metrics:
        limit = max(src_metrics.get("ai_markers", 0) + 1, 1)
        if our_metrics.get("ai_markers", 0) > limit:
            issues.append(f"AI路标词 {our_metrics['ai_markers']}处 (上限{limit})")
    
    if src_metrics and src_metrics.get("pronoun_density", 0) > 0:
        ratio = our_metrics["pronoun_density"] / src_metrics["pronoun_density"]
        if ratio > 1.5 or ratio < 0.5:
            issues.append(f"代词密度 {ratio:.1f}x 偏离源文")
    
    if src_metrics and src_metrics.get("sent_len_stddev", 0) > 0:
        ratio = our_metrics["sent_len_stddev"] / src_metrics["sent_len_stddev"]
        if ratio > 1.5 or ratio < 0.5:
            issues.append(f"句长标准差 {ratio:.1f}x 偏离源文")
    
    if source_text:
        try:
            from lib.plagiarism import find_plagiarism, check_structural_plagiarism
            plagiarisms = find_plagiarism(text, source_text)
            if plagiarisms:
                issues.append(f"台词雷同 {len(plagiarisms)}处（连续≥8字匹配）")
            struct_result = check_structural_plagiarism(text, source_text)
            if struct_result["is_plagiarism"]:
                issues.append(f"结构性抄袭 ({struct_result['score']:.0%})")
        except ImportError:
            pass
    
    return len(issues) == 0, issues


# ============================================================
# 独立函数：供 pipeline 和其他引擎调用
# ============================================================

def trim_chapter(config, ch_num, mode="imitation"):
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    if not ch_file.exists():
        return None
    text = ch_file.read_text(encoding="utf-8")
    return _do_trim(config, ch_num, text, mode)


def polish_chapter(config, ch_num, mode="imitation"):
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    if not ch_file.exists():
        return None
    text = ch_file.read_text(encoding="utf-8")
    return _do_polish(config, ch_num, text, mode, "风格对齐")


def expand_chapter(config, ch_num, mode="imitation", target_chars=None):
    dirs = get_writer_dirs(config)
    ch_file = dirs["chapters_dir"] / f"ch_{ch_num:03d}.txt"
    if not ch_file.exists():
        return None
    text = ch_file.read_text(encoding="utf-8")
    return _do_expand(config, ch_num, text, mode)


def rewrite_chapter(config, ch_num, mode="imitation", reason=""):
    imports = _setup_imports()
    run_one = imports[3]
    try:
        return run_one(config, "write-chapter", ch_num, retry_context=reason or "整章重写")
    except Exception as e:
        print(f"    [ERROR] rewrite 失败: {e}")
        return None
