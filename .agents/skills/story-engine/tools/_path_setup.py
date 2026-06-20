"""统一路径设置：source-engine 共享层 + story-engine 本地。

共享模块（api_client, prompt_meta, state_manager, text_metrics 等）统一在 source-engine/tools/。
story-engine 只保留自己特有的模块。
"""

import sys
from pathlib import Path

# source-engine 共享层（lib/ + 工具模块）
_SOURCE_ENGINE = Path(__file__).resolve().parent.parent.parent / "source-engine" / "tools"

_DIRS = [
    str(_SOURCE_ENGINE),          # prompt_meta, source_io, state_manager, source_analysis
    str(_SOURCE_ENGINE / "lib"),  # api_client, text_metrics, constants, ...
]

for _d in _DIRS:
    if _d not in sys.path:
        sys.path.insert(0, _d)
