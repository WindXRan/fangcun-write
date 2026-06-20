"""统一路径设置：fangcun-novel / fangcun-analyze 三级路径一次性注入。

所有需要导入 prompt_meta / utils / lib 的模块，只需：
    import _path_setup  # noqa: F401  (副作用：设置 sys.path)
    from prompt_meta import ...
"""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent          # fangcun-novel/tools/
_PARENT = _THIS_DIR.parent                           # fangcun-novel/
_SOURCE_ENGINE_TOOLS = _PARENT.parent / "fangcun-analyze" / "tools"

# 按优先级从高到低插入（insert(0) 会让后插入的排在前面）
_DIRS = [
    str(_SOURCE_ENGINE_TOOLS),  # fangcun-analyze/tools/ (最低优先级)
    str(_THIS_DIR),             # fangcun-novel/tools/  (最高优先级)
]

for _d in _DIRS:
    if _d not in sys.path:
        sys.path.insert(0, _d)
