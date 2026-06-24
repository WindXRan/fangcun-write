"""fangcun-write 状态管理器"""

import json
import os
import tempfile
from pathlib import Path
from datetime import datetime


class StateManager:
    """fangcun-write pipeline 的持久化状态管理"""

    PHASE_ORDER = ["open-book", "guides", "write", "postfix", "compare"]

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
                "chapters": {},
                "runs": [],
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

    # Phase 管理
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
        for phase in self.PHASE_ORDER:
            status = self.state["phases"].get(phase, {}).get("status", "pending")
            if status != "done":
                return phase
        return None

    # Chapter 管理
    def chapter_writing(self, ch_num):
        self.state["chapters"][str(ch_num)] = {
            "status": "writing",
            "started": self._now(),
        }

    def chapter_completed(self, ch_num, model="", retries=0):
        self.state["chapters"][str(ch_num)] = {
            "status": "completed",
            "model": model,
            "retries": retries,
            "timestamp": self._now(),
        }

    def chapter_failed(self, ch_num, error=""):
        self.state["chapters"][str(ch_num)] = {
            "status": "failed",
            "error": str(error),
            "timestamp": self._now(),
        }

    def is_chapter_done(self, ch_num):
        return self.state["chapters"].get(str(ch_num), {}).get("status") == "completed"

    def is_chapter_healthy(self, ch_num, filepath=None):
        chapter = self.state.get("chapters", {}).get(str(ch_num), {})
        if chapter.get("status") != "completed":
            return False
        if "error" in chapter:
            return False
        if filepath and not Path(filepath).exists():
            return False
        return True

    def get_completed_chapters(self):
        return sorted(
            int(k) for k, v in self.state.get("chapters", {}).items()
            if v.get("status") == "completed"
        )

    def get_failed_chapters(self):
        return sorted(
            int(k) for k, v in self.state.get("chapters", {}).items()
            if v.get("status") == "failed"
        )

    # 状态摘要
    def summary(self):
        s = self.state
        phases = {k: v.get("status", "?") for k, v in s.get("phases", {}).items()}
        completed = len(self.get_completed_chapters())
        failed = len(self.get_failed_chapters())
        total = len(s.get("chapters", {}))
        return f"phases={phases} chapters={completed}ok/{failed}fail/{total}total"

    def print_status(self):
        print(f"\n项目状态:")
        print(f"  状态文件: {self.state_path}")
        for phase, info in self.state.get("phases", {}).items():
            status = info.get("status", "?")
            extra = ""
            if "completed" in info:
                extra = f" ({info['completed']}个)"
            if "error" in info:
                extra = f" (错误: {info['error'][:50]})"
            print(f"  {phase}: {status}{extra}")
        completed = self.get_completed_chapters()
        failed = self.get_failed_chapters()
        if completed or failed:
            print(f"  章节: {len(completed)} 完成, {len(failed)} 失败")
            if failed:
                print(f"  失败章节: {failed}")


def _atomic_write_json(path, data):
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


def atomic_write_json(path, data):
    """原子写 JSON。"""
    import json
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def atomic_write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=".state_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


