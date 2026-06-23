"""公共工具函数：文件操作、配置验证、进度显示等。"""

import os
import re
import sys
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from lib.constants import CORRUPT_MARKERS
from lib.text_metrics import get_body_chars
from lib.source_locator import get_source_text as _lib_get_source_text, get_total_chapters as _lib_get_total_chapters
from lib.api_client import get_api_url
from logger import log_info, log_warning, log_success, log_fail, log_progress

# 源文缓存（进程内）
_source_cache = {}


def _get_cache_key(config, ch):
    """生成缓存键。"""
    return (config.get("author", ""), config.get("source_book", ""), ch)


def get_source_text(config, ch):
    """读取源文章节原始文本（带内存缓存）。"""
    cache_key = _get_cache_key(config, ch)
    
    text = _source_cache.get(cache_key)
    if text is not None:
        return text
    
    text = _lib_get_source_text(config, ch)
    if text:
        _source_cache[cache_key] = text
    
    return text


def get_total_chapters(config):
    """获取源文总章数。"""
    return _lib_get_total_chapters(config)


def count_source_chars(config, chapter_num):
    """统计源文章节的中文字数（去空白）。"""
    text = get_source_text(config, chapter_num)
    return get_body_chars(text)


def get_source_title(config, chapter_num):
    """从源文章节提取标题（如 第1章 穿、穿书了？）。"""
    from lib.source_locator import find_source_file
    f = find_source_file(config, chapter_num)
    if not f:
        return f"第{chapter_num}章"
    
    try:
        first_line = f.read_text(encoding='utf-8').strip().split('\n')[0]
        if first_line.startswith(f"第{chapter_num}章") or first_line.startswith(f"第{chapter_num:03d}章"):
            return first_line.strip()
    except Exception:
        pass
    
    # fallback: from filename
    stem = f.stem
    if stem.startswith(f"第{chapter_num}章"):
        return stem.strip()
    
    return f"第{chapter_num}章"


def print_progress(done, total, t_start, prefix="  "):
    """打印进度条。"""
    if done % max(1, total // 20) == 0 or done == total:
        log_progress(done, total, t_start, prefix)


def get_chapters_list(config, include_fanwai=False):
    """获取章节目录中的章节列表"""
    base_dir = config.get("base_dir", os.getcwd())
    
    # 优先从 config 读取 source_dir
    source_dir = config.get("source_dir", "")
    if source_dir:
        chapters_dir = Path(base_dir) / source_dir / "chapters"
        if chapters_dir.exists():
            chapters_dir = str(chapters_dir)
        else:
            chapters_dir = None
    else:
        # 兼容旧路径
        author = config.get("author", "")
        source_book = config.get("source_book", "")
        patterns = [
            f"projects/{author}/{source_book}/_cache/chapters/",
            f"projects/{author}/{source_book}/源文/",
        ]
        
        chapters_dir = None
        for pat in patterns:
            full_path = os.path.join(base_dir, pat)
            if os.path.isdir(full_path):
                chapters_dir = full_path
                break
    
    if not chapters_dir:
        return []
    
    # 获取章节列表
    chapters = []
    for f in os.listdir(chapters_dir):
        if not f.endswith('.txt'):
            continue
        if not include_fanwai and '番外' in f:
            continue
        m = re.search(r'(\d+)', f)
        if m:
            chapters.append(int(m.group(1)))
    
    chapters.sort()
    return chapters


def _filter_todo(config, prompt_type, start, end, output_dir, filename_fmt, skip_existing, state_mgr):
    """筛选待处理章节：跳过已存在的、检查 plot_guide 完整性。"""
    todo = []
    empty_plots = set()
    rewrite_set = config.get("_rewrite_chapters")  # 预检指定的章集合

    if prompt_type == "write-chapter":
        guides_dir = Path(config["rewrites_dir"]) / "guides"
        for ch in range(start, end + 1):
            plot_file = guides_dir / f"plot_{ch}.md"
            if not plot_file.exists() or plot_file.stat().st_size == 0:
                empty_plots.add(ch)
                log_warning(f"ch{ch}: plot_{ch}.md 不存在或为空，跳过写章")
                if state_mgr:
                    state_mgr.chapter_failed(ch, error=f"plot_{ch}.md 为空")

    for ch in range(start, end + 1):
        if ch in empty_plots:
            continue
        # 预检模式：只写指定的章
        if rewrite_set is not None and ch not in rewrite_set:
            continue
        if skip_existing:
            filepath = Path(output_dir) / filename_fmt.format(ch=ch)
            if state_mgr and state_mgr.is_chapter_healthy(ch, filepath):
                continue
            if filepath.exists():
                try:
                    text = filepath.read_text(encoding='utf-8')
                    if len(text) >= 500 and not any(marker in text[:500] for marker in CORRUPT_MARKERS):
                        if state_mgr:
                            state_mgr.chapter_completed(ch)
                        continue
                except Exception:
                    pass
        todo.append(ch)

    return todo


def _execute_batch(todo, config, prompt_type, output_dir, filename_fmt, workers, run_one_func, state_mgr, results, errors):
    """并行执行一批任务，返回失败列表。"""
    retry_queue = []
    done, total = 0, len(todo)
    t_start = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_one_func, config, prompt_type, ch): ch for ch in todo}
        for future in as_completed(futures):
            ch = futures[future]
            try:
                content = future.result()
                # 防御：空内容不保存，抛异常触发重试
                if not content or len(content.strip()) < 50:
                    raise ValueError(f"内容为空或过短 ({len(content or '')} chars)")
                path = Path(output_dir) / filename_fmt.format(ch=ch)
                from state_manager import atomic_write_text
                atomic_write_text(path, content)
                results[ch] = str(path)
                if state_mgr:
                    state_mgr.chapter_completed(ch, model=config.get("model", ""))
            except Exception as e:
                errors[ch] = str(e)
                if state_mgr:
                    state_mgr.chapter_failed(ch, error=str(e))
                if len(errors) <= len(todo):
                    retry_queue.append(ch)
            done += 1
            print_progress(done, total, t_start)
            if state_mgr and done % max(1, total // 10) == 0:
                state_mgr.save()

    return retry_queue


def _retry_failed(retry_queue, config, prompt_type, output_dir, filename_fmt, workers, run_one_func, state_mgr, results, errors, max_retries):
    """重试失败章节，最多 max_retries 轮。连续失败3次自动跳过。"""
    skip_chapters = set()  # 连续失败3次的章节
    fail_counts = {}  # 每章失败次数
    
    for retry_round in range(max_retries):
        if not retry_queue:
            break

        # 过滤掉应该跳过的章节
        retry_queue = [ch for ch in retry_queue if ch not in skip_chapters]
        if not retry_queue:
            break

        log_warning(f"[RETRY R{retry_round+1}] 重试 {len(retry_queue)} 章: {retry_queue}")
        retry_todo = retry_queue.copy()
        retry_queue = []

        with ThreadPoolExecutor(max_workers=min(workers, len(retry_todo))) as executor:
            futures = {executor.submit(run_one_func, config, prompt_type, ch): ch for ch in retry_todo}
            for future in as_completed(futures):
                ch = futures[future]
                try:
                    content = future.result()
                    path = Path(output_dir) / filename_fmt.format(ch=ch)
                    from state_manager import atomic_write_text
                    atomic_write_text(path, content)
                    results[ch] = str(path)
                    errors.pop(ch, None)
                    fail_counts.pop(ch, None)  # 重置失败计数
                    if state_mgr:
                        state_mgr.chapter_completed(ch, model=config.get("model", ""))
                    log_success(f"ch{ch} 重试成功")
                except Exception as e:
                    errors[ch] = str(e)
                    fail_counts[ch] = fail_counts.get(ch, 0) + 1
                    
                    if fail_counts[ch] >= 3:
                        skip_chapters.add(ch)
                        log_fail(f"ch{ch} 连续失败3次，跳过")
                    elif retry_round < max_retries - 1:
                        retry_queue.append(ch)
                    
                    if state_mgr:
                        state_mgr.chapter_failed(ch, error=str(e), retries=retry_round + 1)
                    log_fail(f"ch{ch} 重试失败: {e}")

    # 汇总报告
    if skip_chapters:
        log_warning(f"{len(skip_chapters)} 章连续失败3次已跳过: {sorted(skip_chapters)}")
    if retry_queue:
        log_warning(f"{len(retry_queue)} 章在 {max_retries} 次重试后仍然失败: {retry_queue}")

    return retry_queue


def batch_run(config, prompt_type, start, end, workers, output_dir, filename_fmt, 
              skip_existing=False, state_mgr=None, run_one_func=None, max_retries=2):
    """并行批量调用。支持 state_mgr 追踪章节状态。
    
    Args:
        config: 配置字典
        prompt_type: prompt类型
        start: 起始章
        end: 结束章
        workers: 并行数
        output_dir: 输出目录
        filename_fmt: 文件名格式化字符串
        skip_existing: 是否跳过已存在的文件
        state_mgr: 状态管理器
        run_one_func: 单次运行函数（由调用者提供）
        max_retries: 最大重试次数
    
    Returns:
        (results, errors): 成功和失败的章节字典
    """
    results, errors = {}, {}

    todo = _filter_todo(config, prompt_type, start, end, output_dir, filename_fmt, skip_existing, state_mgr)
    if not todo:
        log_info("全部已存在，跳过")
        if state_mgr:
            state_mgr.save()
        return results, errors

    log_info(f"待处理: {len(todo)}章")
    if state_mgr:
        for ch in todo:
            state_mgr.chapter_writing(ch)
        state_mgr.save()

    retry_queue = _execute_batch(todo, config, prompt_type, output_dir, filename_fmt, workers, run_one_func, state_mgr, results, errors)

    if retry_queue:
        _retry_failed(retry_queue, config, prompt_type, output_dir, filename_fmt, workers, run_one_func, state_mgr, results, errors, max_retries)

    if state_mgr:
        state_mgr.save()

    return results, errors


def clear_cache(config=None):
    """清除源文内存缓存。"""
    global _source_cache
    _source_cache.clear()
    print("[OK] 已清除内存缓存")


def get_cache_stats(config):
    """获取缓存统计信息。"""
    return {"memory": len(_source_cache)}


def debug_dump_prompt(config, prompt_type, chapter_num, prompt_path, system_prompt, user_prompt, sp_name, pc):
    """--debug: 保存发给 API 的完整 prompt 到 _debug/ 目录。"""
    base_dir = config.get("base_dir", os.getcwd())
    rewrites_dir = config.get("rewrites_dir", ".")
    debug_dir = (Path(base_dir) / rewrites_dir / "_debug" / prompt_type).resolve()
    debug_dir.mkdir(parents=True, exist_ok=True)

    ch_label = f"{chapter_num:03d}" if chapter_num else "01"
    out = debug_dir / f"ch{ch_label}_{prompt_type}.md"
    content = f"""# Debug: ch{chapter_num or '?'} — {prompt_type}

**Prompt 文件**: `{prompt_path}`
**System Prompt**: `{sp_name}`
**Model**: `{pc.get('model')}`
**Temperature**: `{pc.get('temperature')}`

---

## System Prompt

{system_prompt}

---

## User Prompt

{user_prompt}
"""
    out.write_text(content, encoding="utf-8")
    print(f"  [DEBUG] {out}")
