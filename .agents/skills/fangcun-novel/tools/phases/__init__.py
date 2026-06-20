"""Phase 模块：各个 pipeline 阶段的实现。

自动发现所有 phase_* 和 validate_one 函数，增删模块无需改此文件。"""

from pathlib import Path
import importlib, inspect

__all__ = []
_handlers = {}

for _f in sorted(Path(__file__).parent.glob("*.py")):
    if _f.stem.startswith("_"):
        continue
    _mod = importlib.import_module(f".{_f.stem}", __package__)
    for _name, _obj in inspect.getmembers(_mod, inspect.isfunction):
        if _name.startswith("phase_") or _name == "validate_one":
            globals()[_name] = _obj
            __all__.append(_name)
            _handlers[_name.removeprefix("phase_") if _name.startswith("phase_") else _name] = _obj
