"""统一路径设置：fangcun-write / 共享工具 三级路径一次性注入。

所有需要导入 prompt_meta / utils / lib 的模块，只需：
    import _path_setup  # noqa: F401  (副作用：设置 sys.path)
    from prompt_meta import ...
"""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent          # fangcun-write/tools/
_PARENT = _THIS_DIR.parent                           # fangcun-write/
_SHARED_TOOLS = _PARENT.parent.parent / "tools"      # .agents/tools/

# 按优先级从高到低插入（insert(0) 会让后插入的排在前面）
_DIRS = [
    str(_SHARED_TOOLS),  # .agents/tools/
    str(_THIS_DIR),      # fangcun-write/tools/
]

for _d in _DIRS:
    if _d not in sys.path:
        sys.path.insert(0, _d)

