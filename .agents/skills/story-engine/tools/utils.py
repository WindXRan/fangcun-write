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
from lib.api_client import call_api as _lib_call_api, get_api_url
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


def call_api(api_key, model, user_prompt, reasoning_effort="low", max_tokens=8192, system_prompt=None, api_url=None, max_retries=3, temperature=0.8):
    """调用 API（委托给 lib 模块）。"""
    return _lib_call_api(api_key, model, user_prompt, reasoning_effort, max_tokens, system_prompt, api_url, max_retries, temperature=temperature)


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


def prepend_title(content, title):
    """在章节内容前加上标题行。"""
    lines = content.strip().split('\n')
    # 去掉 LLM 自己生成的标题（如 # 第一章）
    if lines and lines[0].startswith('#'):
        lines = lines[1:]
    if lines and lines[0].strip() == '':
        lines = lines[1:]
    return title + '\n\n' + '\n'.join(lines).strip()


def print_progress(done, total, t_start, prefix="  "):
    """打印进度条。"""
    if done % max(1, total // 20) == 0 or done == total:
        elapsed = time.time() - t_start
        speed = elapsed / done if done > 0 else 0
        eta = speed * (total - done)
        pct = done * 100 // total if total > 0 else 0
        bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)
        log_progress(done, total, t_start, prefix)


def load_trend_knowledge(trend_dir, base_dir):
    """加载热梗知识库文件，返回注入 prompt 的文本块。"""
    td = Path(base_dir) / trend_dir if not Path(trend_dir).is_absolute() else Path(trend_dir)
    if not td.exists() or not td.is_dir():
        return ""
    
    # 按优先级加载知识库文件
    files = [
        ("overview.md", "题材概述"),
        ("mechanics.md", "核心机制/爽点"),
        ("characters.md", "角色模板"),
        ("plot_patterns.md", "情节模式"),
        ("references.md", "参考素材/真实案例"),
        ("keywords.md", "关键词/标签"),
        ("style_notes.md", "风格备注"),
    ]
    
    sections = []
    for fname, label in files:
        fp = td / fname
        if fp.exists():
            try:
                content = fp.read_text(encoding='utf-8').strip()
                if content:
                    sections.append(f"### {label}\n{content}")
            except Exception:
                pass
    
    if not sections:
        return ""
    
    return "\n\n---\n\n## 热梗/题材素材库（开书时参考）\n\n" + "\n\n".join(sections)


def get_chapters_list(config, include_fanwai=False):
    """获取章节目录中的章节列表"""
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    base_dir = config.get("base_dir", os.getcwd())
    
    # 查找章节目录
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
                from prompt_loader import tag_output
                content = tag_output(content, prompt_type)
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
    """重试失败章节，最多 max_retries 轮。"""
    for retry_round in range(max_retries):
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
                    from prompt_loader import tag_output
                    content = tag_output(content, prompt_type)
                    from state_manager import atomic_write_text
                    atomic_write_text(path, content)
                    results[ch] = str(path)
                    errors.pop(ch, None)
                    if state_mgr:
                        state_mgr.chapter_completed(ch, model=config.get("model", ""))
                    log_success(f"ch{ch} 重试成功")
                except Exception as e:
                    errors[ch] = str(e)
                    if state_mgr:
                        state_mgr.chapter_failed(ch, error=str(e), retries=retry_round + 1)
                    if retry_round < max_retries - 1:
                        retry_queue.append(ch)
                    log_fail(f"ch{ch} 重试失败: {e}")

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


class PhaseTimer:
    """流水线阶段耗时统计器。"""

    def __init__(self):
        self.phases = []
        self._current_name = None
        self._current_start = None

    def start(self, name):
        """开始计时一个阶段。会自动结束上一个阶段。"""
        if self._current_name is not None:
            self.end()
        self._current_name = name
        self._current_start = time.time()
        return self

    def end(self, name=None):
        """结束当前阶段或指定阶段。"""
        if name:
            for p in self.phases:
                if p["name"] == name and p["elapsed"] == 0:
                    p["elapsed"] = time.time() - p["start"]
                    return
        if self._current_name is not None and self._current_start is not None:
            elapsed = time.time() - self._current_start
            self.phases.append({
                "name": self._current_name,
                "start": self._current_start,
                "elapsed": round(elapsed, 1),
            })
        self._current_name = None
        self._current_start = None

    def summary(self, total=None):
        """打印耗时汇总表。"""
        if self._current_name is not None:
            self.end()
        if not self.phases:
            return
        total_elapsed = total or sum(p["elapsed"] for p in self.phases)
        print(f"\n{'=' * 60}")
        print(f"  阶段耗时统计")
        print(f"{'=' * 60}")
        print(f"  {'阶段':<28} {'耗时':>8} {'占比':>8}")
        print(f"  {'-' * 46}")
        for p in self.phases:
            pct = p["elapsed"] / total_elapsed * 100 if total_elapsed > 0 else 0
            print(f"  {p['name']:<28} {p['elapsed']:>7.1f}s {pct:>7.1f}%")
        print(f"  {'-' * 46}")
        print(f"  {'合计':<28} {total_elapsed:>7.1f}s {100.0:>7.1f}%")


def clear_cache(config=None):
    """清除源文内存缓存。"""
    global _source_cache
    _source_cache.clear()
    print("[OK] 已清除内存缓存")


def get_cache_stats(config):
    """获取缓存统计信息。"""
    return {"memory": len(_source_cache)}
