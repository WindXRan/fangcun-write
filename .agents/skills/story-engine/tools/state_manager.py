"""状态管理器：持久化 rewrite pipeline 的状态。"""

import os
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime


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
            "5":   {"status": "completed|failed|writing|approved", "retries": 1, "model": "...", "timestamp": "...", "error": "..."},
            "121": {"status": "failed", "retries": 3, "error": "timeout"}
        },
        "runs": [
            {"id": "uuid", "phase": "write", "started": "...", "finished": "...", "model": "...", "range": [1,188], "ok": 180, "fail": 8}
        ],
        "last_review": {
            "timestamp": "...",
            "avg_score": 85,
            "pass": 180,
            "fail": 8,
            "total_issues": 25,
            "high_issues": 3
        }
    }
    """

    CHAPTER_STATUS = {"pending", "writing", "completed", "failed", "approved"}
    PHASE_STATUS = {"pending", "running", "done", "failed"}

    def __init__(self, rewrites_dir):
        self.state_path = Path(rewrites_dir) / "state.json"
        self._state = None

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
            if filepath.exists() and filepath.stat().st_size >= 100:
                return True
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

    def print_status(self):
        """打印详细的项目状态。"""
        print(f"\n项目状态:")
        print(f"  状态文件: {self.state_path}")
        s = self.state
        for phase, info in s.get("phases", {}).items():
            print(f"  {phase}: {info.get('status', '?')}")
        completed = self.get_completed_chapters()
        failed = self.get_failed_chapters()
        print(f"  章节: {len(completed)} 完成, {len(failed)} 失败")
        if failed:
            print(f"  失败章节: {failed}")
        runs = s.get("runs", [])
        if runs:
            print(f"  运行记录: {len(runs)} 次")
            last = runs[-1]
            print(f"    最近: {last.get('phase')} {last.get('range')} ok={last.get('ok')} fail={last.get('fail')}")
        last_review = s.get("last_review")
        if last_review:
            print(f"  最近审查: 平均分={last_review.get('avg_score', 0)} 通过={last_review.get('pass', 0)} 失败={last_review.get('fail', 0)}")


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
