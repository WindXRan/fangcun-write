"""统一路径设置：story-engine / source-engine / lib 三级路径一次性注入。

所有需要导入 prompt_meta / utils / lib 的模块，只需：
    import _path_setup  # noqa: F401  (副作用：设置 sys.path)
    from prompt_meta import ...
"""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent          # story-engine/tools/
_PARENT = _THIS_DIR.parent                           # story-engine/
_SOURCE_ENGINE_TOOLS = _PARENT.parent / "source-engine" / "tools"

_DIRS = [
    str(_THIS_DIR),          # story-engine/tools/  (prompt_meta, utils, ...)
    str(_THIS_DIR / "lib"),  # story-engine/tools/lib/
    str(_SOURCE_ENGINE_TOOLS),  # source-engine/tools/  (共享模块)
]

for _d in _DIRS:
    if _d not in sys.path:
        sys.path.insert(0, _d)
