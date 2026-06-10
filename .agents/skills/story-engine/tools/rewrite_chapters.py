"""
统一改写流水线：Agent/API 双模式兼容。

使用同一套 prompt 文件，prompt_loader 自动适配：
- Agent 模式：prompt 原样返回，Agent 用 Read 工具读文件
- API 模式：自动嵌入【标签】引用的文件内容

流水线（3 阶段）：
  1. 开书 (pro): open-book → concept.md（设定+弧线，含固定角色名）
  2. Guide (flash): plot-guide + style-guide → guides/plot_{N}.md + style_{N}.md
  3. 写章 (flash): write-chapter → chapters/ch_{N}.txt
"""

import os
import re
import sys
import json
import time
import argparse
import tempfile
import requests
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加路径：当前目录（engine/tools）和 story-tools 目录
current_dir = str(Path(__file__).parent)
story_tools_dir = str(Path(__file__).parent.parent.parent / 'story-tools')
sys.path.insert(0, current_dir)
sys.path.insert(0, story_tools_dir)

from prompt_loader import load_prompt

# 共享模块
from lib.constants import AI_MARKERS, CORRUPT_MARKERS, METAPHOR_PATTERN, AI_MARKER_PATTERN, DIRECT_EMOTION_PATTERN
from lib.text_metrics import count_metrics, get_body_chars
from lib.plagiarism import find_plagiarism
from lib.source_locator import get_source_text as _lib_get_source_text, get_source_dir, get_total_chapters as _lib_get_total_chapters
from lib.api_client import call_api as _lib_call_api, get_api_url

# 兼容别名
DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
SYSTEM_PROMPT = "你是一个专业的网文写手，擅长仿写风格迁移。严格按照提供的指南和指令执行。"

# 源文缓存（进程内）
_source_cache = {}


# ============================================================
# StateManager: 持久化状态管理
# ============================================================

class StateManager:
    """管理 rewrite pipeline 的持久化状态。

    状态文件 state.json 结构:
    {
        "version": 1,
        "created": "ISO时间",
        "updated": "ISO时间",
        "phases": {
            "open-book": {"status": "done|running|failed", "started": "...", "finished": "..."},
            "guides":    {"status": "done", "completed_chapters": [1,2,...]},
            "write":     {"status": "in_progress", "completed_chapters": [1,...,120], "failed_chapters": [121]}
        },
        "chapters": {
            "5":   {"status": "completed|failed|writing", "retries": 1, "model": "...", "timestamp": "...", "error": "..."},
            "121": {"status": "failed", "retries": 3, "error": "timeout"}
        },
        "runs": [
            {"id": "uuid", "phase": "write", "started": "...", "finished": "...", "model": "...", "range": [1,188], "ok": 180, "fail": 8}
        ]
    }
    """

    CHAPTER_STATUS = {"pending", "writing", "completed", "failed", "approved"}
    PHASE_STATUS = {"pending", "running", "done", "failed"}

    def __init__(self, rewrites_dir):
        self.state_path = Path(rewrites_dir) / "state.json"
        self._state = None
        self._lock = None  # 未来可加 threading.Lock

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def load(self):
        """加载 state.json，不存在则初始化。"""
        if self.state_path.exists():
            try:
                self._state = json.loads(self.state_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._state = None
        if self._state is None:
            self._state = {
                "version": 1,
                "created": self._now(),
                "updated": self._now(),
                "phases": {},
                "chapters": {},
                "runs": [],
            }
        return self._state

    def save(self):
        """原子写入 state.json。"""
        if self._state is None:
            return
        self._state["updated"] = self._now()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.state_path, self._state)

    @property
    def state(self):
        if self._state is None:
            self.load()
        return self._state

    # ---- Phase 管理 ----

    def phase_start(self, phase_name):
        """标记 phase 开始。"""
        self.state["phases"][phase_name] = {
            "status": "running",
            "started": self._now(),
        }
        self.save()

    def phase_done(self, phase_name, extra=None):
        """标记 phase 完成。"""
        entry = self.state["phases"].get(phase_name, {})
        entry["status"] = "done"
        entry["finished"] = self._now()
        if extra:
            entry.update(extra)
        self.state["phases"][phase_name] = entry
        self.save()

    def phase_failed(self, phase_name, error=""):
        """标记 phase 失败。"""
        entry = self.state["phases"].get(phase_name, {})
        entry["status"] = "failed"
        entry["finished"] = self._now()
        entry["error"] = str(error)
        self.state["phases"][phase_name] = entry
        self.save()

    def is_phase_done(self, phase_name):
        """检查 phase 是否已完成。"""
        return self.state["phases"].get(phase_name, {}).get("status") == "done"

    # ---- Chapter 管理 ----

    def chapter_writing(self, ch_num):
        """标记章节开始写入。"""
        key = str(ch_num)
        self.state["chapters"][key] = {
            "status": "writing",
            "timestamp": self._now(),
        }
        # 不每次都 save，由 batch_run 统一 save

    def chapter_completed(self, ch_num, model="", retries=0):
        """标记章节完成。"""
        key = str(ch_num)
        entry = self.state["chapters"].get(key, {})
        entry["status"] = "completed"
        entry["timestamp"] = self._now()
        entry["model"] = model
        entry["retries"] = retries
        self.state["chapters"][key] = entry

    def chapter_failed(self, ch_num, error="", retries=0):
        """标记章节失败。"""
        key = str(ch_num)
        entry = self.state["chapters"].get(key, {})
        entry["status"] = "failed"
        entry["timestamp"] = self._now()
        entry["error"] = str(error)
        entry["retries"] = retries
        self.state["chapters"][key] = entry

    def chapter_approve(self, ch_num):
        """标记章节人工审核通过。"""
        key = str(ch_num)
        entry = self.state["chapters"].get(key, {})
        entry["status"] = "approved"
        entry["approved_at"] = self._now()
        self.state["chapters"][key] = entry
        self.save()

    def save_review_result(self, ch_num, score, issues):
        """保存审查结果到章节状态。"""
        key = str(ch_num)
        entry = self.state["chapters"].get(key, {})
        entry["review_score"] = score
        entry["review_issues"] = len(issues)
        entry["review_high"] = sum(1 for i in issues if i.get("severity") == "high")
        entry["review_at"] = self._now()
        self.state["chapters"][key] = entry

    def save_review_report(self, report):
        """保存完整审查报告摘要到 state。"""
        summary = report.get("summary", {})
        self.state["last_review"] = {
            "timestamp": self._now(),
            "avg_score": summary.get("avg_score", 0),
            "pass": summary.get("pass", 0),
            "fail": summary.get("fail", 0),
            "total_issues": summary.get("total_issues", 0),
            "high_issues": summary.get("high_issues", 0),
        }
        # 保存每章的审查结果
        for ch_str, ch_data in report.get("chapters", {}).items():
            ch = int(ch_str)
            self.save_review_result(ch, ch_data.get("score", 0), ch_data.get("issues", []))
        self.save()

    def get_chapter_status(self, ch_num):
        """获取章节状态。"""
        return self.state["chapters"].get(str(ch_num), {}).get("status", "pending")

    def get_chapters_by_status(self, status):
        """获取指定状态的所有章节号。"""
        return sorted(
            int(k) for k, v in self.state["chapters"].items()
            if v.get("status") == status
        )

    def get_completed_chapters(self):
        """获取所有已完成/已审核的章节号。"""
        return sorted(
            int(k) for k, v in self.state["chapters"].items()
            if v.get("status") in ("completed", "approved")
        )

    def get_failed_chapters(self):
        """获取所有失败的章节号。"""
        return self.get_chapters_by_status("failed")

    # ---- Run 历史 ----

    def add_run(self, phase, start, end, model=""):
        """记录一次运行，返回 run_id。"""
        run_id = f"{phase}_{int(time.time())}"
        entry = {
            "id": run_id,
            "phase": phase,
            "started": self._now(),
            "range": [start, end],
            "model": model,
        }
        self.state["runs"].append(entry)
        self.save()
        return run_id

    def finish_run(self, run_id, ok=0, fail=0):
        """更新运行结果。"""
        for run in self.state["runs"]:
            if run["id"] == run_id:
                run["finished"] = self._now()
                run["ok"] = ok
                run["fail"] = fail
                break
        self.save()

    # ---- 健康检查 ----

    def is_chapter_healthy(self, ch_num, filepath):
        """综合检查章节是否健康：state.json + 文件内容。"""
        status = self.get_chapter_status(ch_num)
        if status in ("completed", "approved"):
            # state 说完成，再验证文件存在
            if filepath.exists():
                return True
        # state 说 pending/failed/writing，或文件不存在，都不健康
        return False

    # ---- 摘要 ----

    def summary(self):
        """返回可读的状态摘要。"""
        s = self.state
        phases = {k: v.get("status", "?") for k, v in s.get("phases", {}).items()}
        total = len(s.get("chapters", {}))
        completed = len(self.get_completed_chapters())
        failed = len(self.get_failed_chapters())
        runs = len(s.get("runs", []))
        return f"phases={phases} chapters={completed}ok/{failed}fail/{total}total runs={runs}"


def atomic_write_json(path, data):
    """原子写入 JSON：先写临时文件，再 rename。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=".state_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))  # 原子替换
    except Exception:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_text(path, content):
    """原子写入文本文件：先写临时文件，再 rename。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=".ch_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def get_api_url(config=None):
    """获取API URL，优先级：配置文件 > 环境变量 > 默认值。确保包含 /v1。"""
    base = None
    if config and config.get("api_base_url"):
        base = config["api_base_url"].rstrip("/")
    elif os.environ.get("API_BASE_URL"):
        base = os.environ.get("API_BASE_URL").rstrip("/")
    if base:
        # 确保包含 /v1
        if not base.endswith("/v1"):
            base = base + "/v1"
        return base + "/chat/completions"
    return DEFAULT_API_URL


def validate_config(config):
    """校验配置完整性，返回错误列表。"""
    errors = []
    required = ["book_name", "author", "source_book", "rewrites_dir"]
    for key in required:
        if not config.get(key):
            errors.append(f"缺少必填字段: {key}")
    
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        errors.append("未配置 API_KEY（config.api_key 或 $env:API_KEY）")
    
    return errors


def find_source_chapter(config, chapter_num):
    """查找源文章节文件路径。返回 Path 或 None。"""
    from lib.source_locator import find_source_file
    return find_source_file(config, chapter_num)


def get_source_text(config, ch):
    """读取源文章节原始文本（带缓存）。"""
    cache_key = (config.get("author", ""), config.get("source_book", ""), ch)
    if cache_key in _source_cache:
        return _source_cache[cache_key]
    text = _lib_get_source_text(config, ch)
    _source_cache[cache_key] = text
    return text


def call_api(api_key, model, user_prompt, reasoning_effort="low", max_tokens=8192, system_prompt=None, api_url=None, max_retries=3):
    """调用 API（委托给 lib 模块）。"""
    return _lib_call_api(api_key, model, user_prompt, reasoning_effort, max_tokens, system_prompt, api_url, max_retries)


def get_total_chapters(config):
    """获取源文总章数。"""
    return _lib_get_total_chapters(config)


def count_source_chars(config, chapter_num):
    """统计源文章节的中文字数（去空白）。"""
    text = get_source_text(config, chapter_num)
    return get_body_chars(text)
    return len(re.sub(r'\s', '', text))


def run_one(config, prompt_type, chapter_num=None, model=None, reasoning_effort=None, system_prompt=None, extra_replacements=None):
    """执行单次调用。通过 prompt_loader 加载并嵌入文件内容。"""
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

    # open-book 需要动态样本章节（开局5章+中间3章+最后5章）
    if prompt_type == "open-book" and total_ch > 0:
        # 开局5章
        replacements["章号_开篇1"] = "1"
        replacements["章号_开篇2"] = "2"
        replacements["章号_开篇3"] = "3"
        replacements["章号_开篇4"] = "4"
        replacements["章号_开篇5"] = "5"
        # 中间3章（25%/50%/75%位置）
        replacements["章号_中段1"] = str(max(1, int(total_ch * 0.25)))
        replacements["章号_中段2"] = str(max(1, int(total_ch * 0.50)))
        replacements["章号_中段3"] = str(max(1, int(total_ch * 0.75)))
        # 最后5章（跳过番外）
        import re as re_tail
        tail_chs = []
        for c in range(total_ch, 0, -1):
            tail_title = get_source_title(config, c)
            if '番外' in tail_title:
                continue
            tail_chs.append(str(c))
            if len(tail_chs) >= 5:
                break
        tail_chs.reverse()
        for i in range(5):
            replacements[f"章号_结尾{i+1}"] = tail_chs[i] if i < len(tail_chs) else str(total_ch)

    # 需要源文字数时，脚本计算（API 无法跑 PowerShell）
    if prompt_type in ("plot-guide", "style-guide", "write-chapter", "trim-chapter") and chapter_num:
        src_chars = count_source_chars(config, chapter_num)
        target_chars = src_chars  # 1:1对标源文字数
        replacements["源文字数"] = str(src_chars)
        replacements["目标字数"] = str(target_chars)
        replacements["目标字数_min"] = str(int(target_chars * 0.9))
        replacements["目标字数_max"] = str(int(target_chars * 1.1))
    
    # style-guide注入源文指标（用脚本提取）
    if prompt_type == "style-guide" and chapter_num:
        metrics = get_source_metrics(config, chapter_num)
        if metrics:
            replacements["源文指标"] = metrics
        else:
            replacements["源文指标"] = "（提取失败，请手动统计）"

    # plot-guide和write-chapter注入角色名（从concept.md提取）
    if prompt_type in ("plot-guide", "write-chapter") and chapter_num:
        concept_path = Path(config["rewrites_dir"]) / "concept.md"
        if concept_path.exists():
            import re as re_concept
            concept_text = concept_path.read_text(encoding='utf-8')
            # 提取角色设定部分
            m = re_concept.search(r'## 角色设定.*?(?=##|\Z)', concept_text, re_concept.DOTALL)
            if m:
                role_block = m.group()
                # 提取女主、男主、配角名
                female = re_concept.search(r'女主\*\*：(\S+?)[，,]', role_block)
                male = re_concept.search(r'男主\*\*：(\S+?)[，,]', role_block)
                if female:
                    replacements["女主名"] = female.group(1)
                if male:
                    replacements["男主名"] = male.group(1)

    max_tokens = 8192  # 不限制，靠重跑兜底

    # 合并额外替换变量（如串行模式的上一章摘要）
    if extra_replacements:
        replacements.update(extra_replacements)

    prompt_path = f"{prompts_dir}/{prompt_type}.md"
    user_prompt = load_prompt(prompt_path, base_dir, replacements, mode="api")

    # 写章时使用每章独立的 style_guide（通过 prompt 中的【style_guide】标签引用）
    sys_prompt = system_prompt or SYSTEM_PROMPT

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


def save_file(dir_path, filename, content):
    """保存文件（原子写入）。"""
    path = Path(dir_path) / filename
    atomic_write_text(path, content)
    return str(path)


def get_source_title(config, chapter_num):
    """从源文章节提取标题（如 第1章 穿、穿书了？）。"""
    f = find_source_chapter(config, chapter_num)
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


# ============================================================
# Phase 0: Prep（提取元数据+章节目录）
# ============================================================

def phase_prep(config):
    """从原始 TXT 提取头部元数据和章节目录，供 open-book 使用。兼容 projects/ 下各种目录结构。"""
    import glob as g

    base_dir = config.get("base_dir", os.getcwd())
    author = config.get("author", "")
    source_book = config.get("source_book", "")

    cache_dir = Path(base_dir) / "projects" / author / source_book / "_cache"
    os.makedirs(cache_dir, exist_ok=True)

    # 1. 提取原始 TXT 头部（书名/作者/简介/标签/等级体系）
    header_file = cache_dir / "_header.txt"
    if not header_file.exists():
        # 多路径搜索原始 TXT
        raw_paths = [
            Path(base_dir) / "projects" / f"{source_book}.txt",
            Path(base_dir) / "projects" / author / f"{source_book}.txt",
            Path(base_dir) / "projects" / author / source_book / f"{source_book}.txt",
            Path(base_dir) / "projects" / author / f"{source_book}.txt",
            Path(base_dir) / f"{source_book}.txt",
        ]
        raw_txt = None
        for p in raw_paths:
            if p.exists():
                raw_txt = p
                break

        if raw_txt:
            with open(raw_txt, encoding='utf-8') as f:
                head_lines = []
                for i, line in enumerate(f):
                    if i >= 80:
                        break
                    stripped = line.strip()
                    # 多种章节标题模式：第1章 / 第一章 / 第001章 / Chapter 1
                    if stripped and (
                        (stripped.startswith('第') and '章' in stripped[:15]) or
                        stripped.lower().startswith('chapter')
                    ):
                        break
                    head_lines.append(line)
            header_file.write_text(''.join(head_lines), encoding='utf-8')
            print(f"[OK] _header.txt ({len(head_lines)}行) -> {raw_txt}")
        else:
            print(f"[WARN] 未找到原始 TXT，_header.txt 跳过")

    # 2. 生成章节目录（从已拆分的章节）
    toc_file = cache_dir / "_toc.txt"
    if not toc_file.exists():
        # 多路径搜索拆分章节
        chapters_dirs = [
            cache_dir / "chapters",
            Path(base_dir) / "projects" / author / source_book / "源文",
            Path(base_dir) / "projects" / author / source_book / "源文",
        ]
        chapter_files = []
        for d in chapters_dirs:
            if d.exists():
                import re as re_toc
                cf = sorted(
                    d.glob("第*章*.txt"),
                    key=lambda f: int(re_toc.search(r'第(\d+)章', f.stem).group(1)) if re_toc.search(r'第(\d+)章', f.stem) else 0
                )
                if cf:
                    chapter_files = cf
                    break

        if chapter_files:
            toc_lines = [f"总章数: {len(chapter_files)}\n\n"]
            import re as re_title
            for cf in chapter_files:
                try:
                    first_line = cf.read_text(encoding='utf-8').strip().split('\n')[0]
                    # 只取前60字（标题行），去掉空白
                    title = first_line.strip()[:60]
                    toc_lines.append(title)
                except:
                    toc_lines.append(cf.stem)
            toc_file.write_text('\n'.join(toc_lines), encoding='utf-8')
            print(f"[OK] _toc.txt ({len(chapter_files)}章，含完整标题)")
        else:
            print(f"[WARN] 未找到拆分章节，_toc.txt 跳过")


# ============================================================
# Phase 1: 开书
# ============================================================

def phase_open_book(config, state_mgr=None):
    """生成 concept.md（设定 + 弧线，含固定角色名）。"""
    print("\n" + "=" * 50)
    print("Phase 1: 开书 (pro, reasoning=high)")
    print("=" * 50)

    if state_mgr:
        if state_mgr.is_phase_done("open-book"):
            print("concept.md 已完成，跳过")
            return True
        state_mgr.phase_start("open-book")

    pro = {**config, "model": "deepseek-v4-pro", "reasoning_effort": "high"}
    try:
        concept = run_one(pro, "open-book")
        path = save_file(config["rewrites_dir"], "concept.md", concept)
        print(f"[OK] concept.md → {path}")
        if state_mgr:
            state_mgr.phase_done("open-book")
        return True
    except Exception as e:
        print(f"[FAIL] concept.md: {e}")
        if state_mgr:
            state_mgr.phase_failed("open-book", error=str(e))
        return False


# ============================================================
# Phase 1.5: 风格分析（每章独立）
# ============================================================

def phase_style_analysis(config):
    """用 style_analyzer.py 生成每章的 style_guide。"""
    import subprocess
    
    author = config.get("author", "")
    source_book = config.get("source_book", "")
    base_dir = config.get("base_dir", os.getcwd())
    rewrites_dir = config["rewrites_dir"]
    
    # 查找源文目录
    src_patterns = [
        f"projects/{author}/{source_book}/_cache/chapters/",
        f"projects/{author}/{source_book}/源文/",
    ]
    
    src_dir = None
    for pat in src_patterns:
        full = os.path.join(base_dir, pat)
        if os.path.isdir(full):
            src_dir = full
            break
    
    if not src_dir:
        print("[FAIL] 未找到源文目录")
        return False
    
    # 输出目录
    guides_dir = os.path.join(rewrites_dir, "guides")
    os.makedirs(guides_dir, exist_ok=True)
    
    # 运行 style_analyzer.py
    script_path = os.path.join(base_dir, "tools/style_analyzer.py")
    if not os.path.exists(script_path):
        # 尝试从 story-engine tools 目录查找
        script_path = Path(__file__).parent.parent.parent / "tools/style_analyzer.py"
    
    print(f"\n{'=' * 50}")
    print(f"Phase 1.5: 风格分析 (脚本)")
    print("=" * 50)
    
    try:
        result = subprocess.run(
            ["python", str(script_path), src_dir, guides_dir],
            capture_output=True,
            timeout=300,
            cwd=base_dir
        )
        if result.returncode == 0:
            print(f"[OK] 风格分析完成")
            return True
        else:
            print(f"[FAIL] 风格分析失败: {result.stderr.decode('utf-8', errors='ignore')}")
            return False
    except Exception as e:
        print(f"[FAIL] 风格分析: {e}")
        return False


# ============================================================
# Phase 2: Guide 生成
# ============================================================


def phase_guides(config, start, end, workers=5, serial=False, state_mgr=None):
    """生成 plot_guide + style_guide（引用 templates）。"""
    guides_dir = f"{config['rewrites_dir']}/guides"
    style_analysis_dir = config.get("style_analysis_dir", f"{config['rewrites_dir']}/../style_analysis")
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    if state_mgr:
        state_mgr.phase_start("guides")

    # style-guide（引用 templates）
    print(f"\n{'=' * 50}")
    print(f"Phase 2: style_guide (flash, ch{start}-{end}, 引用 templates)")
    print("=" * 50)

    ok_style, fail_style = batch_run(flash, "style-guide", start, end, workers, guides_dir,
                                     "style_{ch}.md", skip_existing=True, state_mgr=state_mgr)
    print(f"style_guide: OK={len(ok_style)} FAIL={len(fail_style)}")

    # plot-guide
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
                path = save_file(guides_dir, f"plot_{ch}.md", result)
                ok[ch] = path
                import re as re_p
                beats = re_p.findall(r'新书[：:].*?(?=\n|$)', result)
                if not beats:
                    beats = re_p.findall(r'节拍\d+[：:].*?(?=\n|$)', result)
                prev_summary = '；'.join(beats[-3:]) if beats else result[-300:]
                print(f"  [OK] ch{ch} plot-guide")
            except Exception as e:
                fail[ch] = str(e)
                print(f"  [FAIL] ch{ch}: {e}")
    else:
        ok, fail = batch_run(flash, "plot-guide", start, end, workers, guides_dir,
                             "plot_{ch}.md", skip_existing=True, state_mgr=state_mgr)

    print(f"plot_guide: OK={len(ok)} FAIL={len(fail)}")

    if state_mgr:
        if fail or fail_style:
            state_mgr.phase_failed("guides", error=f"plot:{len(fail)} fail, style:{len(fail_style)} fail")
        else:
            state_mgr.phase_done("guides")


# ============================================================
# Phase 3: 写章
# ============================================================

def phase_write(config, start, end, workers=10, state_mgr=None):
    """并行写章 + 异常章自动重跑（字数触发）。"""
    import re as re2
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    print(f"\n{'=' * 50}")
    print(f"Phase 3: 写章 (flash, ch{start}-{end}, {workers}w)")
    print("=" * 50)

    if state_mgr:
        state_mgr.phase_start("write")

    t0 = time.time()

    # 记录运行
    run_id = None
    if state_mgr:
        run_id = state_mgr.add_run("write", start, end, model="deepseek-v4-flash")

    # 第一轮
    ok, fail = batch_run(flash, "write-chapter", start, end, workers, chapters_dir,
                         "ch_{ch:03d}.txt", skip_existing=True, state_mgr=state_mgr)

    # 重跑异常章（最多2轮）
    for retry_round in range(1, 3):
        retry_list = []
        for ch in range(start, end + 1):
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            if not ch_file.exists():
                continue
            text = ch_file.read_text(encoding='utf-8')

            target = count_source_chars(config, ch)
            chars = len(re2.sub(r'\s', '', text.split('\n', 1)[1] if '\n' in text else text))
            if target > 0:
                deviation = abs(chars - target) / target
                if deviation > 0.3:
                    retry_list.append((ch, f"字数{chars}/{target}"))
            elif chars < 900 or chars > 3000:
                retry_list.append((ch, f"字数{chars}"))

        if not retry_list:
            break

        print(f"  [RETRY R{retry_round}] {len(retry_list)}章异常: {[(c, w) for c,w in retry_list]}")
        for ch, _ in retry_list:
            ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
            ch_file.unlink(missing_ok=True)
            if state_mgr:
                state_mgr.chapter_writing(ch)  # 重置为 writing

        ok2, fail2 = batch_run(flash, "write-chapter",
            min(c for c, _ in retry_list), max(c for c, _ in retry_list),
            workers, chapters_dir, "ch_{ch:03d}.txt", skip_existing=False, state_mgr=state_mgr)
        ok.update(ok2)
        fail.update(fail2)

    total = sum(
        len(Path(path).read_text(encoding='utf-8').replace('\n','').replace(' ','').replace('\r',''))
        for path in ok.values()
    )
    print(f"  完成: OK={len(ok)} FAIL={len(fail)} 总字数≈{total} | 耗时 {time.time()-t0:.0f}s")

    if state_mgr:
        if fail:
            state_mgr.phase_failed("write", error=f"{len(fail)}章失败")
        else:
            state_mgr.phase_done("write", extra={"total_chars": total})
        if run_id:
            state_mgr.finish_run(run_id, ok=len(ok), fail=len(fail))

    return ok, fail


# ============================================================
# 批量并行
# ============================================================

def batch_run(config, prompt_type, start, end, workers, output_dir, filename_fmt, skip_existing=False, state_mgr=None):
    """并行批量调用。支持 state_mgr 追踪章节状态。"""
    results, errors = {}, {}
    todo = []

    # 损坏文件特征词（扩展列表）
    CORRUPT_MARKERS = ['抱歉', '无法读取', '无法生成', '对不起', '作为AI', '作为语言模型', '我无法']

    for ch in range(start, end + 1):
        if skip_existing:
            filename = filename_fmt.format(ch=ch)
            filepath = Path(output_dir) / filename
            # 优先用 state.json 判断
            if state_mgr and state_mgr.is_chapter_healthy(ch, filepath):
                continue
            if filepath.exists():
                try:
                    text = filepath.read_text(encoding='utf-8')
                    if len(text) < 500:
                        pass
                    elif any(marker in text[:500] for marker in CORRUPT_MARKERS):
                        pass
                    else:
                        # 文件健康但 state 未记录，补记
                        if state_mgr:
                            state_mgr.chapter_completed(ch)
                        continue
                except Exception:
                    pass
        todo.append(ch)

    if not todo:
        print(f"  全部已存在，跳过")
        if state_mgr:
            state_mgr.save()
        return results, errors

    print(f"  待处理: {len(todo)}章")
    if state_mgr:
        for ch in todo:
            state_mgr.chapter_writing(ch)
        state_mgr.save()

    done, total = 0, len(todo)
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_one, config, prompt_type, ch): ch for ch in todo}
        for future in as_completed(futures):
            ch = futures[future]
            try:
                content = future.result()
                filename = filename_fmt.format(ch=ch)
                path = save_file(output_dir, filename, content)
                results[ch] = path
                if state_mgr:
                    state_mgr.chapter_completed(ch, model=config.get("model", ""))
            except Exception as e:
                errors[ch] = str(e)
                if state_mgr:
                    state_mgr.chapter_failed(ch, error=str(e))
            done += 1
            if done % max(1, total // 20) == 0 or done == total:
                elapsed = time.time() - t_start
                speed = elapsed / done
                eta = speed * (total - done)
                pct = done * 100 // total
                bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)
                print(f"  [{done}/{total}] [{bar}] {pct}% | {elapsed:.0f}s | ETA {eta:.0f}s")
                if state_mgr:
                    state_mgr.save()  # 每 5% 持久化一次
    if state_mgr:
        state_mgr.save()
    return results, errors


# ============================================================
# Phase 3.1: Validate（后处理验证）
# ============================================================

def count_chapter_metrics(text):
    """统计章节的量化指标（委托给 lib 模块）。"""
    return count_metrics(text)


def get_source_metrics(config, ch):
    """直接从源文章节计算锚点指标（不依赖 LLM 填写的 style_guide）。"""
    text = get_source_text(config, ch)
    if text:
        return count_chapter_metrics(text)
    return None


def validate_one(config, ch):
    """验证单章质量：源文指标 vs 仿写指标。返回 (pass: bool, report: str)。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"

    if not ch_file.exists():
        return False, f"ch{ch:03d}: 文件不存在"

    text = ch_file.read_text(encoding='utf-8')
    metrics = count_chapter_metrics(text)
    src = get_source_metrics(config, ch)
    src_text = get_source_text(config, ch)  # 用于台词抄袭检测

    issues = []
    warnings = []

    # 1. 字数检查（对标源文）
    target = count_source_chars(config, ch)
    if target > 0:
        deviation = (metrics["chars"] - target) / target
        if deviation > 0.15:
            issues.append(f"字数超标 {metrics['chars']}/{target} (+{deviation:.0%})")
        elif deviation < -0.15:
            issues.append(f"字数不足 {metrics['chars']}/{target} ({deviation:.0%})")
        elif abs(deviation) > 0.10:
            warnings.append(f"字数偏差 {metrics['chars']}/{target} ({deviation:+.0%})")

    # 2. 比喻句检查（不超过源文+3）
    if src:
        limit = src["metaphor"] + 3
        if metrics["metaphor"] > limit:
            issues.append(f"比喻过多 {metrics['metaphor']} (源文{src['metaphor']}, 上限{limit})")

    # 4. AI 路标词（源文水平+2以内）
    if src:
        limit = max(src["ai_markers"] + 1, 1)  # 收紧AI痕迹
        if metrics["ai_markers"] > limit:
            issues.append(f"AI路标词 {metrics['ai_markers']}处 (源文{src['ai_markers']}, 上限{limit})")

    # 5. 直抒情（源文水平+2以内）
    if src:
        limit = max(src["direct_emotion"] + 2, 3)
        if metrics["direct_emotion"] > limit:
            issues.append(f"直抒情 {metrics['direct_emotion']}处 (源文{src['direct_emotion']}, 上限{limit})")

    # 6. 台词抄袭检测（连续8字以上与源文重合）
    if src_text:
        import re as re_s
        # 构建源文所有8-gram集合（O(n)）
        src_clean = re_s.sub(r'[。！？…\n\s]+', '', src_text)
        src_grams = set()
        for i in range(len(src_clean) - 7):
            src_grams.add(src_clean[i:i+8])
        
        # 检测仿写文中的8-gram匹配
        imt_clean = re_s.sub(r'[。！？…\n\s]+', '', text)
        plagiarisms = []
        matched_ranges = []
        i = 0
        while i < len(imt_clean) - 7:
            gram = imt_clean[i:i+8]
            if gram in src_grams:
                # 找到匹配，扩展找最长匹配
                j = i + 8
                while j < len(imt_clean) and imt_clean[i:j+1] in src_grams:
                    j += 1
                match_len = j - i
                # 避免重叠计数
                if not matched_ranges or i >= matched_ranges[-1][1]:
                    plagiarisms.append((imt_clean[max(0,i-5):i+20], match_len))
                    matched_ranges.append((i, j))
                i = j
            else:
                i += 1
        
        if len(plagiarisms) > 0:
            issues.append(f"台词雷同 {len(plagiarisms)}处（连续≥8字匹配）")
            for p in plagiarisms[:3]:
                issues.append(f"  '{p[0]}...' ({p[1]}字重合)")

    # 汇总
    all_ok = len(issues) == 0
    status = "[PASS]" if all_ok else "[FAIL]"
    report_parts = [f"ch{ch:03d} {status} | {metrics['chars']}字 | metaphor={metrics['metaphor']} | AI={metrics['ai_markers']} | direct_emo={metrics['direct_emotion']}"]
    if src:
        report_parts.append(f"  源文: {src['chars']}字 | metaphor={src['metaphor']} | AI={src['ai_markers']} | direct_emo={src['direct_emotion']}")
    for i in issues:
        report_parts.append(f"  *ISSUE* {i}")
    for w in warnings:
        report_parts.append(f"  *WARN* {w}")

    return all_ok, '\n'.join(report_parts)


def phase_validate(config, start, end):
    """验证章节质量，报告不达标指标。返回详细结果列表。"""
    print(f"\n{'=' * 50}")
    print(f"Phase 3.1: 质量验证 (ch{start}-{end})")
    print("=" * 50)

    results = []
    ok_count, fail_count = 0, 0
    for ch in range(start, end + 1):
        passed, report = validate_one(config, ch)
        print(report)
        if passed:
            ok_count += 1
            results.append({'ch': ch, 'status': 'PASS'})
        else:
            fail_count += 1
            results.append({'ch': ch, 'status': 'FAIL'})

    if fail_count > 0:
        print(f"\n[WARN] {fail_count}章不达标，建议手动修改或重写。")
    else:
        print(f"\n[OK] 全部通过")

    return results


# ============================================================
# Phase 3.2: Post-Fix（机械后处理——不调LLM）
# ============================================================

def phase_postfix(config, start, end):
    """机械修复：段尾补省略号、去#号、砍超标字数。不调LLM。"""
    import re
    chapters_dir = f"{config['rewrites_dir']}/chapters"

    print(f"\n{'=' * 50}")
    print(f"Phase 3.2: 后处理 (ch{start}-{end})")
    print("=" * 50)

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            continue

        text = ch_file.read_text(encoding='utf-8')
        lines = text.strip().split('\n')
        fixed = 0

        # 1. 去标题 # 号；过滤源文标题；删重复标题行
        if lines and lines[0].startswith('# '):
            lines[0] = lines[0][2:]
            fixed += 1
        src_title = get_source_title(config, ch)
        if src_title and lines and lines[0].strip() == src_title.strip():
            lines[0] = f"第{ch}章"  # 替换为通用标题
            fixed += 1
        # 删除紧跟标题后的重复标题行（如 line 0 和 line 2 都是"第N章"）
        if len(lines) >= 3 and lines[2].startswith('第') and '章' in lines[2][:10]:
            del lines[2]  # 删掉重复标题
            if len(lines) > 2 and lines[2].strip() == '':
                del lines[2]  # 顺便删空行
            fixed += 1

        if fixed > 0:
            ch_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            print(f"  ch{ch:03d}: {fixed}处修复")
        else:
            print(f"  ch{ch:03d}: 无需修复")

    return True


# ============================================================
# Phase 3.5: Post-Trim
# ============================================================

def phase_trim(config, start, end):
    """超字数章节自动精简（>20% 偏差触发）。"""
    import re
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    print(f"\n{'=' * 50}")
    print(f"Phase 3.5: 字数精简 (ch{start}-{end})")
    print("=" * 50)

    trimmed = 0
    total_chapters = end - start + 1
    done_chapters = 0
    t_start = time.time()

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            done_chapters += 1
            continue

        text = ch_file.read_text(encoding='utf-8')
        lines = text.strip().split('\n')
        body = '\n'.join(lines[1:]) if lines and lines[0].startswith('第') else text
        chars = len(re.sub(r'\s', '', body))
        target = count_source_chars(config, ch)

        if target == 0:
            done_chapters += 1
            continue

        over = (chars - target) / target
        if over <= 0.2:
            done_chapters += 1
            continue  # 在 ±20% 内，跳过

        print(f"  [TRIM] ch{ch:03d}: {chars}->{target} ({over:+.0%})")
        try:
            result = run_one(flash, "trim-chapter", ch)
            # 保留原标题
            title = lines[0] if lines and lines[0].startswith('第') else f"第{ch}章"
            ch_file.write_text(title + '\n\n' + result.strip(), encoding='utf-8')
            trimmed += 1
        except Exception as e:
            print(f"  [FAIL] trim ch{ch}: {e}")

        # 更新进度
        done_chapters += 1
        if done_chapters % max(1, total_chapters // 20) == 0 or done_chapters == total_chapters:
            elapsed = time.time() - t_start
            speed = elapsed / done_chapters
            eta = speed * (total_chapters - done_chapters)
            pct = done_chapters * 100 // total_chapters
            bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)
            print(f"  [{done_chapters}/{total_chapters}] [{bar}] {pct}% | {elapsed:.0f}s | ETA {eta:.0f}s")

    if trimmed:
        print(f"\n[OK] 精简了 {trimmed} 章")
    else:
        print(f"\n所有章节在 ±20% 内，无需精简")
    return trimmed


# ============================================================
# Phase 3.6: 整章重写（人设崩塌、节奏失控时使用）
# ============================================================

def phase_rewrite(config, start, end, workers=5):
    """整章重写：保留guide，从头重写正文。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    print(f"\n{'=' * 50}")
    print(f"Phase 3.6: 整章重写 (ch{start}-{end}, {workers}w)")
    print("=" * 50)

    rewritten = 0
    total_chapters = end - start + 1
    done_chapters = 0
    t_start = time.time()

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            done_chapters += 1
            continue

        print(f"  [REWRITE] ch{ch:03d}")
        try:
            # 删除旧文件，重新生成
            ch_file.unlink(missing_ok=True)
            result = run_one(flash, "write-chapter", ch)
            
            # 生成标题
            title = f"第{ch}章"
            ch_file.write_text(title + '\n\n' + result.strip(), encoding='utf-8')
            rewritten += 1
        except Exception as e:
            print(f"  [FAIL] rewrite ch{ch}: {e}")

        # 更新进度
        done_chapters += 1
        if done_chapters % max(1, total_chapters // 20) == 0 or done_chapters == total_chapters:
            elapsed = time.time() - t_start
            speed = elapsed / done_chapters
            eta = speed * (total_chapters - done_chapters)
            pct = done_chapters * 100 // total_chapters
            bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)
            print(f"  [{done_chapters}/{total_chapters}] [{bar}] {pct}% | {elapsed:.0f}s | ETA {eta:.0f}s")

    if rewritten:
        print(f"\n[OK] 重写了 {rewritten} 章")
    return rewritten


# ============================================================
# Phase 3.7: 润色（只改文笔，不改内容）
# ============================================================

def phase_polish(config, start, end, workers=5):
    """润色：只改文笔（删AI味、加细节、改对话），不改情节。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    print(f"\n{'=' * 50}")
    print(f"Phase 3.7: 润色 (ch{start}-{end}, {workers}w)")
    print("=" * 50)

    polished = 0
    total_chapters = end - start + 1
    done_chapters = 0
    t_start = time.time()

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            done_chapters += 1
            continue

        original = ch_file.read_text(encoding='utf-8')
        orig_chars = len(original.replace('\n', '').replace(' ', ''))

        prompt = f"""你是专业网文写手。请润色以下章节，提升文笔质量。

【润色要求】
1. 不改变情节、人物、对话内容
2. 删除AI痕迹（「仿佛」「似乎」「不禁」「心中涌起」等）
3. 增加细节描写（五感、环境、动作）
4. 优化句式，避免排比句连续超过3句
5. 对话更自然，像真人说话
6. 字数控制在原文±10%以内（{int(orig_chars*0.9)}~{int(orig_chars*1.1)}字）

【原文】
{original}

【输出格式】
直接输出润色后的完整章节，不要解释。"""

        try:
            result = call_api(
                flash.get("api_key") or os.environ.get("API_KEY"),
                flash.get("model", "deepseek-v4-flash"),
                prompt,
                reasoning_effort="low",
                max_tokens=8000,
                system_prompt="你是专业网文写手，擅长润色文笔。保持情节不变，只改表达。",
                api_url=get_api_url(flash)
            )
            
            new_chars = len(result.replace('\n', '').replace(' ', ''))
            
            # 检查字数差异
            if orig_chars > 0 and abs(new_chars - orig_chars) / orig_chars > 0.15:
                print(f"  [SKIP] ch{ch:03d}: 字数差异过大 ({orig_chars}→{new_chars})")
            else:
                ch_file.write_text(result, encoding='utf-8')
                polished += 1
                print(f"  [POLISH] ch{ch:03d}: {orig_chars}→{new_chars}字")
        except Exception as e:
            print(f"  [FAIL] polish ch{ch}: {e}")

        # 更新进度
        done_chapters += 1
        if done_chapters % max(1, total_chapters // 20) == 0 or done_chapters == total_chapters:
            elapsed = time.time() - t_start
            speed = elapsed / done_chapters
            eta = speed * (total_chapters - done_chapters)
            pct = done_chapters * 100 // total_chapters
            bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)
            print(f"  [{done_chapters}/{total_chapters}] [{bar}] {pct}% | {elapsed:.0f}s | ETA {eta:.0f}s")

    if polished:
        print(f"\n[OK] 润色了 {polished} 章")
    return polished


# ============================================================
# Phase 3.8: 扩写（增加内容扩充字数）
# ============================================================

def phase_expand(config, start, end, target_ratio=1.3, workers=5):
    """扩写：增加内容扩充字数，默认扩充30%。"""
    chapters_dir = f"{config['rewrites_dir']}/chapters"
    flash = {**config, "model": "deepseek-v4-flash", "reasoning_effort": "low"}

    print(f"\n{'=' * 50}")
    print(f"Phase 3.8: 扩写 (ch{start}-{end}, 目标+{(target_ratio-1)*100:.0f}%, {workers}w)")
    print("=" * 50)

    expanded = 0
    total_chapters = end - start + 1
    done_chapters = 0
    t_start = time.time()

    for ch in range(start, end + 1):
        ch_file = Path(chapters_dir) / f"ch_{ch:03d}.txt"
        if not ch_file.exists():
            done_chapters += 1
            continue

        original = ch_file.read_text(encoding='utf-8')
        orig_chars = len(original.replace('\n', '').replace(' ', ''))
        target_chars = int(orig_chars * target_ratio)

        # 检查是否需要扩写
        source_chars = count_source_chars(config, ch)
        if source_chars > 0 and orig_chars >= source_chars * 0.9:
            done_chapters += 1
            continue  # 字数已够，跳过

        prompt = f"""你是专业网文写手。请扩写以下章节，增加内容使字数达到{target_chars}字左右。

【扩写要求】
1. 保持原有情节框架和人物关系
2. 增加细节描写（环境、心理、动作）
3. 增加对话互动
4. 增加场景过渡
5. 不要增加新的情节线
6. 字数控制在{int(target_chars*0.9)}~{int(target_chars*1.1)}字

【原文（{orig_chars}字）】
{original}

【输出格式】
直接输出扩写后的完整章节，不要解释。"""

        try:
            result = call_api(
                flash.get("api_key") or os.environ.get("API_KEY"),
                flash.get("model", "deepseek-v4-flash"),
                prompt,
                reasoning_effort="low",
                max_tokens=10000,
                system_prompt="你是专业网文写手，擅长扩写内容。保持情节不变，增加细节。",
                api_url=get_api_url(flash)
            )
            
            new_chars = len(result.replace('\n', '').replace(' ', ''))
            
            # 检查字数
            if new_chars < orig_chars * 1.1:
                print(f"  [SKIP] ch{ch:03d}: 扩写不足 ({orig_chars}→{new_chars})")
            else:
                ch_file.write_text(result, encoding='utf-8')
                expanded += 1
                print(f"  [EXPAND] ch{ch:03d}: {orig_chars}→{new_chars}字 (+{(new_chars/orig_chars-1)*100:.0f}%)")
        except Exception as e:
            print(f"  [FAIL] expand ch{ch}: {e}")

        # 更新进度
        done_chapters += 1
        if done_chapters % max(1, total_chapters // 20) == 0 or done_chapters == total_chapters:
            elapsed = time.time() - t_start
            speed = elapsed / done_chapters
            eta = speed * (total_chapters - done_chapters)
            pct = done_chapters * 100 // total_chapters
            bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)
            print(f"  [{done_chapters}/{total_chapters}] [{bar}] {pct}% | {elapsed:.0f}s | ETA {eta:.0f}s")

    if expanded:
        print(f"\n[OK] 扩写了 {expanded} 章")
    return expanded


# ============================================================
# Phase 4.5: 全文审稿（调用full_review.py）
# ============================================================

def phase_review(config, start, end, batch_size=20, workers=5):
    """全文审稿：调用full_review.py进行分批审稿+汇总分析。"""
    import subprocess

    print(f"\n{'=' * 50}")
    print(f"Phase 4.5: 全文审稿 (ch{start}-{end})")
    print("=" * 50)

    config_file = config.get("config_file")
    if not config_file:
        print("[FAIL] 未指定配置文件，请在配置中添加 config_file 字段")
        return

    cmd = [
        "python", ".agents/skills/story-review/tools/full_review.py",
        "--config", config_file,
        "--start", str(start),
        "--end", str(end),
        "--batch-size", str(batch_size),
        "--workers", str(workers)
    ]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True, encoding='utf-8', timeout=1800)
        if result.returncode == 0:
            print("[OK] 全文审稿完成")
        else:
            print(f"[FAIL] 全文审稿失败: {result.stderr}")
    except Exception as e:
        print(f"[FAIL] 全文审稿失败: {e}")


# ============================================================
# Phase 5: 全文修复（调用full_fix.py）
# ============================================================

def phase_fix(config, start, end, workers=5):
    """全文修复：调用full_fix.py根据审稿报告并行修复章节。"""
    import subprocess

    print(f"\n{'=' * 50}")
    print(f"Phase 5: 全文修复 (ch{start}-{end})")
    print("=" * 50)

    config_file = config.get("config_file")
    if not config_file:
        print("[FAIL] 未指定配置文件，请在配置中添加 config_file 字段")
        return

    cmd = [
        "python", ".agents/skills/story-review/tools/full_fix.py",
        "--config", config_file,
        "--start", str(start),
        "--end", str(end),
        "--workers", str(workers)
    ]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True, encoding='utf-8', timeout=1800)
        if result.returncode == 0:
            print("[OK] 全文修复完成")
        else:
            print(f"[FAIL] 全文修复失败: {result.stderr}")
    except Exception as e:
        print(f"[FAIL] 全文修复失败: {e}")


# ============================================================
# Phase 6: 统一审查+修复（新系统）
# ============================================================

def phase_unified_check(config, start, end, workers=10, batch_size=25, state_mgr=None):
    """统一检查：算法+LLM分批审核，只检查不修复。"""
    print(f"\n{'=' * 50}")
    print(f"统一检查 (ch{start}-{end})")
    print("=" * 50)

    from unified_fixer import run_pipeline

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = config.get("api_base_url", "https://api.deepseek.com").rstrip("/") + "/v1/chat/completions"
    model = config.get("model", "deepseek-chat")

    results, merged = run_pipeline(
        config, start, end, api_key, api_url, model,
        batch_size=batch_size, workers=workers, dry_run=True,
    )

    if state_mgr and merged:
        for ch, data in merged.items():
            state_mgr.save_review_result(ch, data.get("score", 0), data.get("issues", []))
        state_mgr.save()

    return merged


def phase_unified_fix(config, start, end, workers=10, batch_size=25, dry_run=False):
    """统一审改：分批审核→合并→制定任务→执行修复。"""
    print(f"\n{'=' * 50}")
    print(f"统一审改 (ch{start}-{end}, dry_run={dry_run})")
    print("=" * 50)

    from unified_fixer import run_pipeline

    api_key = config.get("api_key") or os.environ.get("API_KEY")
    api_url = config.get("api_base_url", "https://api.deepseek.com").rstrip("/") + "/v1/chat/completions"
    model = config.get("model", "deepseek-chat")

    if not api_key:
        print("[WARN] 未配置 API_KEY，将跳过 LLM 审核和修复")

    results, merged = run_pipeline(
        config, start, end, api_key, api_url, model,
        batch_size=batch_size, workers=workers, dry_run=dry_run,
    )

    # 保存
    output = os.path.join(config['rewrites_dir'], 'compare', 'unified_review_fix.json')
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": {str(k): v for k, v in (results or {}).items()},
        "merged": {str(k): v for k, v in (merged or {}).items()},
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  结果已保存: {output}")

    return results


def phase_unified_review_fix(config, start, end, workers=10, batch_size=25, state_mgr=None):
    """统一审改（推荐）：分批审核→合并→制定任务→执行修复。"""
    results = phase_unified_fix(config, start, end, workers=workers, batch_size=batch_size, dry_run=False)

    if state_mgr and results:
        for ch, r in (results or {}).items():
            if isinstance(r, dict) and r.get("status") == "fixed":
                state_mgr.chapter_completed(ch, model="mixed", retries=0)
        state_mgr.save()

    return results


# ============================================================
# Phase 4: 对比
# ============================================================

def phase_compare(config, start, end, batch_size=10):
    """生成仿写 vs 源文对比报告（分批处理）"""
    import subprocess

    rewrites_dir = config["rewrites_dir"]
    compare_dir = f"{rewrites_dir}/compare"
    compare_script = ".agents/skills/story-compare/compare.py"

    print(f"\n{'=' * 50}")
    print(f"Phase 4: 对比 (ch{start}-{end}, 每{batch_size}章一批)")
    print("=" * 50)
    
    # 清理旧的对比报告
    for old_file in Path(compare_dir).glob("对比_*.md"):
        old_file.unlink()
    for old_file in Path(compare_dir).glob("源文_*.txt"):
        old_file.unlink()
    for old_file in Path(compare_dir).glob("新书_*.txt"):
        old_file.unlink()
    print("已清理旧对比报告")

    # 分批处理
    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end)
        print(f"\n  对比第{batch_start}-{batch_end}章...")
        
        cmd = ["python", compare_script, rewrites_dir, str(batch_start), str(batch_end)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=120)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            compare_dir = f"{rewrites_dir}/compare"
            print(f"  [OK] 对比_{batch_start}-{batch_end}_报告.md")
            print(f"  [OK] 对比_{batch_start}-{batch_end}_AI分析.md")
        except Exception as e:
            print(f"  [FAIL] 第{batch_start}-{batch_end}章对比失败: {e}")

    print(f"\n对比报告 → {rewrites_dir}/compare/")


def open_reader(config):
    """自动启动新版阅读器（story-scan）"""
    import webbrowser
    import subprocess
    import glob
    
    rewrites_dir = config.get("rewrites_dir", "")
    if not rewrites_dir:
        return
    
    # story-scan目录
    scan_dir = ".agents/skills/story-scan"
    
    # 查找书籍文件
    book_files = glob.glob(f"{rewrites_dir}/chapters/ch_*.txt")
    if not book_files:
        print("[WARN] 未找到章节文件，跳过自动打开")
        return
    
    # 获取第一本书的路径（相对于项目根目录）
    first_book = book_files[0].replace("\\", "/")
    
    # 检查web服务器是否已运行
    web_running = False
    api_running = False
    
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:8000", timeout=2)
        web_running = True
    except:
        pass
    
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:8001", timeout=2)
        api_running = True
    except:
        pass
    
    # 启动缺失的服务器
    if not web_running:
        print("启动web服务器...")
        try:
            subprocess.Popen(
                ["python", "-m", "http.server", "8000"],
                cwd=scan_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            print(f"[WARN] 启动web服务器失败: {e}")
    
    if not api_running:
        print("启动API服务器...")
        try:
            subprocess.Popen(
                ["python", "api/book_content.py"],
                cwd=scan_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            print(f"[WARN] 启动API服务器失败: {e}")
    
    # 等待服务器启动
    import time
    time.sleep(2)
    
    # 打开阅读器
    url = f"http://localhost:8000/book.html?file={first_book}"
    print(f"阅读器地址: {url}")
    webbrowser.open(url)


# ============================================================
# 主入口
# ============================================================

def get_chapters_list(config, include_fanwai=False):
    """获取章节目录中的章节列表"""
    import glob
    import re
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


def all_with_fix(config, start, end, workers=10, max_rounds=3, state_mgr=None):
    """一键完成：生成→统一审查→统一修复→输出报告。

    Args:
        config: 配置
        start: 起始章
        end: 结束章
        workers: 并行数
        max_rounds: 最大修复轮数
        state_mgr: StateManager 实例
    """
    print(f"\n{'=' * 60}")
    print(f"一键完成流程 (ch{start}-{end}, 最多{max_rounds}轮修复)")
    print("=" * 60)

    start_time = time.time()

    # ============ 第1步：生成章节 ============
    print(f"\n{'=' * 50}")
    print(f"第1步：生成章节")
    print("=" * 50)

    phase_guides(config, start, end, workers, state_mgr=state_mgr)

    batch_size = 10
    for batch_start in range(start, end + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end)
        phase_write(config, batch_start, batch_end, workers, state_mgr=state_mgr)
        phase_postfix(config, batch_start, batch_end)

    # ============ 第2步：统一审查+修复 ============
    report = phase_unified_review_fix(config, start, end, workers=workers, state_mgr=state_mgr)

    # ============ 第3步：生成报告 ============
    print(f"\n{'=' * 50}")
    print(f"第3步：生成完本报告")
    print("=" * 50)

    summary = report.get("summary", {}) if report else {}
    final_pass = summary.get("pass", 0)
    final_fail = summary.get("fail", 0)

    all_rounds = []
    if report:
        all_rounds.append({
            "round": 1,
            "pass": final_pass,
            "fail": final_fail,
            "avg_score": summary.get("avg_score", 0),
            "total_issues": summary.get("total_issues", 0),
        })

    generate_completion_report(config, start, end, all_rounds, final_pass, final_fail, start_time)

    # 导出TXT
    print("\n导出完整TXT...")
    try:
        from merge_chapters import merge_chapters
        chapters_dir = f"{config['rewrites_dir']}/chapters"
        export_dir = f"{config['rewrites_dir']}/export"
        export_file = f"{export_dir}/{config['book_name']}.txt"
        concept_path = f"{config['rewrites_dir']}/concept.md"
        os.makedirs(export_dir, exist_ok=True)
        if merge_chapters(chapters_dir, export_file, 'utf-8', concept_path):
            print(f"[OK] 已导出: {export_file}")
    except Exception as e:
        print(f"[WARN] 导出失败: {e}")

    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"一键完成！")
    print("=" * 60)
    print(f"总章节：{end - start + 1}章")
    total = final_pass + final_fail
    if total > 0:
        print(f"最终通过率：{final_pass}/{total} ({final_pass/total*100:.1f}%)")
    print(f"平均分：{summary.get('avg_score', 0)}")
    print(f"总问题数：{summary.get('total_issues', 0)}")
    print(f"总耗时：{total_time:.0f}秒")
    print(f"\n报告位置：{config['rewrites_dir']}/完本报告.md")
    
    return report


def generate_completion_report(config, start, end, all_rounds, final_pass, final_fail, start_time):
    """生成完本报告。"""
    import time
    
    rewrites_dir = config['rewrites_dir']
    report_file = Path(rewrites_dir) / "完本报告.md"
    
    # 计算总字数
    chapters_dir = Path(rewrites_dir) / "chapters"
    total_chars = 0
    chapter_count = 0
    if chapters_dir.exists():
        for ch_file in sorted(chapters_dir.glob("ch_*.txt")):
            content = ch_file.read_text(encoding='utf-8')
            lines = content.strip().split('\n')
            if lines and lines[0].startswith('第'):
                content = '\n'.join(lines[1:])
            total_chars += len(content.replace('\n', '').replace(' ', ''))
            chapter_count += 1
    
    # 生成报告
    report = f"""# 完本报告

## 项目信息

| 项目 | 内容 |
|------|------|
| 书名 | {config.get('book_name', '未知')} |
| 作者 | {config.get('author', '未知')} |
| 总章节 | {chapter_count}章 |
| 总字数 | {total_chars:,}字 |
| 平均每章 | {total_chars//chapter_count if chapter_count else 0:,}字 |

## 修复历史

| 轮次 | 通过 | 未通过 | 修复操作 |
|------|------|--------|----------|
"""
    
    for round_info in all_rounds:
        fixes = '、'.join(round_info.get('fixes', []))
        report += f"| 第{round_info['round']}轮 | {round_info['pass']}章 | {round_info['fail']}章 | {fixes} |\n"
    
    report += f"""
## 最终质量

| 指标 | 数值 |
|------|------|
| 通过章节 | {final_pass}章 |
| 未通过章节 | {final_fail}章 |
| 通过率 | {final_pass/(final_pass+final_fail)*100:.1f}% |

## 文件清单

```
{rewrites_dir}/
├── concept.md
├── guides/
│   ├── plot_*.md
│   └── style_*.md
├── chapters/
│   └── ch_*.txt
├── compare/
│   └── *.md
├── export/
│   └── {config.get('book_name', '书名')}.txt
└── 完本报告.md
```

## 后续建议

"""
    
    if final_fail > 0:
        report += f"""仍有{final_fail}章未通过验证，建议：
1. 手动检查未通过章节
2. 运行 `python tools/rewrite_chapters.py --config {config.get('config_file', 'configs/xxx.json')} --phase review --start {start} --end {end}` 进行审稿修复
"""
    else:
        report += """所有章节已通过验证！可以进行投稿。
"""
    
    report += f"""
---
*报告生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # 保存报告
    report_file.write_text(report, encoding='utf-8')
    print(f"报告已保存：{report_file}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description="统一改写流水线")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=10)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--serial", action="store_true",
                        help="plot-guide 串行生成，保持章间连贯（质量模式）")
    parser.add_argument("--phase", default="all",
                        help="all | all-with-fix | unified | unified-check | unified-fix | full-review | open-book | guides | write | validate | trim | rewrite | polish | expand | compare | review | fix")
    parser.add_argument("--include-fanwai", action="store_true",
                        help="包含番外章节（默认不包含）")
    parser.add_argument("--max-fix-rounds", type=int, default=3,
                        help="最大修复轮数（默认3轮）")
    parser.add_argument("--status", action="store_true",
                        help="显示当前项目状态后退出")

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding='utf-8'))
    config.setdefault("prompts_dir", ".agents/skills/story-engine/prompts")
    config.setdefault("base_dir", os.getcwd())

    # 配置校验
    errors = validate_config(config)
    if errors:
        print("配置错误:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # 初始化状态管理
    rewrites_dir = config.get("rewrites_dir", "")
    state_mgr = StateManager(rewrites_dir) if rewrites_dir else None
    if state_mgr:
        state_mgr.load()
        print(f"[STATE] {state_mgr.summary()}")

    # --status: 显示状态后退出
    if args.status:
        if state_mgr:
            print(f"\n项目状态:")
            print(f"  状态文件: {state_mgr.state_path}")
            s = state_mgr.state
            for phase, info in s.get("phases", {}).items():
                print(f"  {phase}: {info.get('status', '?')}")
            completed = state_mgr.get_completed_chapters()
            failed = state_mgr.get_failed_chapters()
            print(f"  章节: {len(completed)} 完成, {len(failed)} 失败")
            if failed:
                print(f"  失败章节: {failed}")
            runs = s.get("runs", [])
            if runs:
                print(f"  运行记录: {len(runs)} 次")
                last = runs[-1]
                print(f"    最近: {last.get('phase')} {last.get('range')} ok={last.get('ok')} fail={last.get('fail')}")
        else:
            print("未初始化状态管理")
        return

    # 如果没有指定 --end，则自动获取最大章节号（默认不包含番外）
    if not any('--end' in arg for arg in sys.argv):
        chapters = get_chapters_list(config, include_fanwai=args.include_fanwai)
        if chapters:
            args.end = max(chapters)
            print(f"自动检测到最大章节: 第{args.end}章")

    if args.workers is None:
        args.workers = args.end - args.start + 1
        print(f"workers 自动设为章节数: {args.workers}")

    print(f"改写流水线 | {config['book_name']} | ch{args.start}-{args.end} | workers={args.workers}")
    print(f"项目目录: {rewrites_dir}")

    t0 = time.time()
    phases = set(args.phase.split(","))

    if "all" in phases or "prep" in phases or "open-book" in phases:
        phase_prep(config)

    if "all" in phases or "open-book" in phases:
        phase_open_book(config, state_mgr=state_mgr)

    if "all" in phases or "guides" in phases:
        phase_guides(config, args.start, args.end, args.workers, serial=args.serial, state_mgr=state_mgr)

    if "all" in phases or "write" in phases:
        batch_size = 10
        for batch_start in range(args.start, args.end + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, args.end)
            print(f"\n{'#' * 50}")
            print(f" 批次: 第{batch_start}-{batch_end}章")
            print(f"{'#' * 50}")

            phase_write(config, batch_start, batch_end, args.workers, state_mgr=state_mgr)
            phase_postfix(config, batch_start, batch_end)
            phase_compare(config, batch_start, batch_end)

        open_reader(config)

    if "all" in phases or "validate" in phases:
        phase_validate(config, args.start, args.end)

    if "all" in phases or "trim" in phases:
        phase_trim(config, args.start, args.end)

    if "rewrite" in phases:
        phase_rewrite(config, args.start, args.end, args.workers)

    if "polish" in phases:
        phase_polish(config, args.start, args.end, args.workers)

    if "expand" in phases:
        phase_expand(config, args.start, args.end, workers=args.workers)

    if "review" in phases:
        phase_review(config, args.start, args.end, args.workers)

    if "fix" in phases:
        phase_fix(config, args.start, args.end, args.workers)

    # 统一检查（只检查不修复）
    if "unified-check" in phases:
        phase_unified_check(config, args.start, args.end, workers=args.workers, state_mgr=state_mgr)

    # 统一修复（检查+修复一次搞定）
    if "unified-fix" in phases:
        phase_unified_fix(config, args.start, args.end, workers=args.workers)

    # 统一审查+修复（推荐，一次搞定）
    if "unified" in phases:
        phase_unified_review_fix(config, args.start, args.end, workers=args.workers, state_mgr=state_mgr)

    # 自动 Prompt 优化（审稿后自动运行，优化/精简/扩充 prompt）
    if "optimize" in phases:
        try:
            from auto_prompt_optimize import run_optimize
            run_optimize(config, args.start, args.end, mode="auto")
        except ImportError:
            print("[WARN] auto_prompt_optimize.py 未找到，跳过 prompt 优化")

    if "full-review" in phases:
        # 完整审改流程：审核→规划→执行→验证（委托 story-review）
        import subprocess as _sp
        config_file = config.get("config_file")
        if not config_file:
            print("[FAIL] 未指定配置文件，请在配置中添加 config_file 字段")
        else:
            cmd = [
                "python", ".agents/skills/story-review/tools/novel_review_rewrite.py",
                "--config", config_file,
                "--start", str(args.start),
                "--end", str(args.end),
                "--workers", str(args.workers)
            ]
            try:
                result = _sp.run(cmd, capture_output=False, text=True, encoding='utf-8', timeout=3600)
                if result.returncode == 0:
                    print("[OK] 完整审改流程完成")
                else:
                    print(f"[FAIL] 完整审改流程失败")
            except Exception as e:
                print(f"[FAIL] 完整审改流程失败: {e}")

    if "all" in phases or "compare" in phases:
        phase_compare(config, args.start, args.end)

    # all-with-fix：一键完成生成→验证→审稿→修复→重新验证→输出报告
    if "all-with-fix" in phases:
        all_with_fix(config, args.start, args.end, args.workers, args.max_fix_rounds, state_mgr=state_mgr)

    # 自动导出完整TXT
    if "all" in phases or "write" in phases:
        print(f"\n{'=' * 50}")
        print("自动导出完整TXT...")
        print("=" * 50)
        try:
            from merge_chapters import merge_chapters
            chapters_dir = f"{config['rewrites_dir']}/chapters"
            export_dir = f"{config['rewrites_dir']}/export"
            export_file = f"{export_dir}/{config['book_name']}.txt"
            concept_path = f"{config['rewrites_dir']}/concept.md"
            os.makedirs(export_dir, exist_ok=True)
            if merge_chapters(chapters_dir, export_file, 'utf-8', concept_path):
                print(f"[OK] 已导出: {export_file}")
            else:
                print(f"[WARN] 导出失败")
        except Exception as e:
            print(f"[WARN] 导出失败: {e}")

    # 生成最终汇报
    total_time = time.time() - t0
    rewrites_dir = config.get('rewrites_dir', '')
    
    print(f"\n{'=' * 50}")
    print(f"仿写完成！结果：")
    print("=" * 50)
    
    # 生成文件列表
    print(f"\n生成文件：")
    rewrites_path = Path(rewrites_dir)
    if rewrites_path.exists():
        print(f"- {rewrites_dir}/")
        
        # 检查各文件
        files_to_check = [
            ("concept.md", "设定+弧线"),
        ]
        for filename, desc in files_to_check:
            filepath = rewrites_path / filename
            if filepath.exists():
                print(f"  - {filename} - {desc}")
        
        # 检查guides目录
        guides_dir = rewrites_path / "guides"
        if guides_dir.exists():
            plot_files = list(guides_dir.glob("plot_*.md"))
            style_files = list(guides_dir.glob("style_*.md"))
            print(f"  - guides/ - {len(plot_files)}章plot+style指南")
        
        # 检查chapters目录
        chapters_dir = rewrites_path / "chapters"
        if chapters_dir.exists():
            chapter_files = sorted(chapters_dir.glob("ch_*.txt"))
            if chapter_files:
                print(f"  - chapters/ch_001.txt ~ ch_{len(chapter_files):03d}.txt - {len(chapter_files)}章正文")
        
        # 检查compare目录
        compare_dir = rewrites_path / "compare"
        if compare_dir.exists():
            print(f"  - compare/ - 对比报告")
            compare_files = list(compare_dir.glob("*"))
            for cf in compare_files:
                print(f"    - {cf.name}")
    
    # 统计信息
    print(f"\n统计：")
    # 计算总字数
    chapters_dir = rewrites_path / "chapters"
    if chapters_dir.exists():
        total_chars = 0
        for ch_file in chapters_dir.glob("ch_*.txt"):
            content = ch_file.read_text(encoding='utf-8')
            # 去除标题行和空白
            lines = content.strip().split('\n')
            if lines and lines[0].startswith('第'):
                content = '\n'.join(lines[1:])
            total_chars += len(content.replace('\n', '').replace(' ', ''))
        print(f"- 总字数：{total_chars:,}字")
    
    # 获取源文字数
    source_chars = config.get("source_chars", 0)
    if source_chars:
        print(f"- 源文字数：{source_chars:,}字")
    
    print(f"- 耗时：{total_time:.0f}秒")
    
    # 质量验证结果
    if "validate" in phases:
        print(f"\n质量验证：")
        # 这里可以添加验证结果的统计
    
    print(f"\n如需审稿修复，可运行：")
    print(f"python .agents/skills/story-engine/tools/rewrite_chapters.py --config {args.config} --phase review --start {args.start} --end {args.end}")


if __name__ == '__main__':
    main()
