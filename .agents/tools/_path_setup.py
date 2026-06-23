"""统一路径设置：fangcun-analyze / lib 两级路径一次性注入。

所有需要导入 prompt_meta / lib 的模块，只需：
    import _path_setup  # noqa: F401  (副作用：设置 sys.path)
    from lib.api_client import ...
"""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent          # fangcun-analyze/tools/
_NOVEL_DIR = _THIS_DIR.parent.parent / "fangcun-novel" / "tools"  # fallback to fangcun-novel/tools/

_DIRS = [
    str(_THIS_DIR),          # fangcun-analyze/tools/  (source_io, ...)
    str(_THIS_DIR / "lib"),  # fangcun-analyze/tools/lib/
    str(_NOVEL_DIR),         # fangcun-novel/tools/ (prompt_meta, ...)
]

for _d in _DIRS:
    if _d not in sys.path:
        sys.path.insert(0, _d)
