"""fangcun-drama 状态管理器：跟踪 pipeline 进度，支持断点续传。"""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime


class StateManager:
    """管理 fangcun-drama pipeline 的持久化状态。

    state.json 结构:
    {
        "version": 1,
        "created": "ISO时间",
        "updated": "ISO时间",
        "phases": {
            "event":      {"status": "done", "started": "...", "finished": "...", "completed": 153, "failed": 0},
            "skeleton":   {"status": "done", "started": "...", "finished": "..."},
            "adaptation": {"status": "running", "started": "..."},
            "script":     {"status": "pending"},
            "review":     {"status": "pending"},
            "export":     {"status": "pending"}
        },
        "episodes": {
            "1":  {"status": "completed", "chars": 1702},
            "2":  {"status": "completed", "chars": 1581},
            "3":  {"status": "failed", "error": "timeout"}
        }
    }
    """

    PHASE_ORDER = ["event", "skeleton", "skeleton_review", "adaptation", "adaptation_review", "script", "export"]

    def __init__(self, output_dir):
        self.state_path = Path(output_dir) / "state.json"
        self._state = None

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def load(self):
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
                "episodes": {},
            }
        return self._state

    def save(self):
        if self._state is None:
            return
        self._state["updated"] = self._now()
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(self.state_path, self._state)

    @property
    def state(self):
        if self._state is None:
            self.load()
        return self._state

    # ─── Phase 管理 ───

    def phase_start(self, phase_name):
        self.state["phases"][phase_name] = {
            "status": "running",
            "started": self._now(),
        }
        self.save()

    def phase_done(self, phase_name, extra=None):
        entry = self.state["phases"].get(phase_name, {})
        entry["status"] = "done"
        entry["finished"] = self._now()
        if extra:
            entry.update(extra)
        self.state["phases"][phase_name] = entry
        self.save()

    def phase_failed(self, phase_name, error=""):
        entry = self.state["phases"].get(phase_name, {})
        entry["status"] = "failed"
        entry["finished"] = self._now()
        entry["error"] = str(error)
        self.state["phases"][phase_name] = entry
        self.save()

    def is_phase_done(self, phase_name):
        return self.state["phases"].get(phase_name, {}).get("status") == "done"

    def get_resume_phase(self):
        """找到第一个未完成的 phase，用于断点续传。"""
        for phase in self.PHASE_ORDER:
            status = self.state["phases"].get(phase, {}).get("status", "pending")
            if status != "done":
                return phase
        return None  # 全部完成

    # ─── Episode 管理 ───

    def episode_completed(self, ep_num, chars=0):
        self.state["episodes"][str(ep_num)] = {
            "status": "completed",
            "chars": chars,
            "timestamp": self._now(),
        }

    def episode_failed(self, ep_num, error=""):
        self.state["episodes"][str(ep_num)] = {
            "status": "failed",
            "error": str(error),
            "timestamp": self._now(),
        }

    def is_episode_done(self, ep_num):
        return self.state["episodes"].get(str(ep_num), {}).get("status") == "completed"

    def get_completed_episodes(self):
        return sorted(
            int(k) for k, v in self.state["episodes"].items()
            if v.get("status") == "completed"
        )

    def get_failed_episodes(self):
        return sorted(
            int(k) for k, v in self.state["episodes"].items()
            if v.get("status") == "failed"
        )

    # ─── 状态摘要 ───

    def summary(self):
        s = self.state
        phases = {k: v.get("status", "?") for k, v in s.get("phases", {}).items()}
        completed = len(self.get_completed_episodes())
        failed = len(self.get_failed_episodes())
        return f"phases={phases} episodes={completed}ok/{failed}fail"

    def print_status(self):
        print(f"\n项目状态:")
        print(f"  状态文件: {self.state_path}")
        for phase, info in self.state.get("phases", {}).items():
            status = info.get("status", "?")
            extra = ""
            if "completed" in info:
                extra = f" ({info['completed']}章)"
            if "error" in info:
                extra = f" (错误: {info['error'][:50]})"
            print(f"  {phase}: {status}{extra}")
        completed = self.get_completed_episodes()
        failed = self.get_failed_episodes()
        if completed or failed:
            print(f"  剧本: {len(completed)} 完成, {len(failed)} 失败")
            if failed:
                print(f"  失败集数: {failed}")


def _atomic_write_json(path, data):
    """原子写入 JSON。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=".state_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
