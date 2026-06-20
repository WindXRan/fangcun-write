"""统一路径设置：source-engine / lib 两级路径一次性注入。

所有需要导入 prompt_meta / lib 的模块，只需：
    import _path_setup  # noqa: F401  (副作用：设置 sys.path)
    from lib.api_client import ...
"""

import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent          # source-engine/tools/

_DIRS = [
    str(_THIS_DIR),          # source-engine/tools/  (prompt_meta, source_io, ...)
    str(_THIS_DIR / "lib"),  # source-engine/tools/lib/
]

for _d in _DIRS:
    if _d not in sys.path:
        sys.path.insert(0, _d)
