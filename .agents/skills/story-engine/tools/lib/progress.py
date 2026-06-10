"""进度条打印工具。"""

import time


def print_progress(done, total, start_time, prefix=""):
    """打印进度条和 ETA。

    Args:
        done: 已完成数
        total: 总数
        start_time: 开始时间 (time.time())
        prefix: 前缀文字
    """
    if total == 0:
        return

    elapsed = time.time() - start_time
    speed = elapsed / done if done > 0 else 0
    eta = speed * (total - done)
    pct = done * 100 // total
    bar = '=' * (pct // 5) + '>' + ' ' * (20 - pct // 5)

    parts = [f"[{done}/{total}] [{bar}] {pct}%"]
    if prefix:
        parts.insert(0, prefix)
    parts.append(f"{elapsed:.0f}s")
    if done < total:
        parts.append(f"ETA {eta:.0f}s")

    print(f"  {' | '.join(parts)}")
