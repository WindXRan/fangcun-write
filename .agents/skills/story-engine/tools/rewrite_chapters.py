"""统一改写流水线（向后兼容入口）。

此文件是 pipeline.py 的薄包装层，保持向后兼容性。
新的模块化结构请直接使用 pipeline.py 或 phases/ 目录下的模块。
"""

# 导入新的模块化结构
from pipeline import main
from state_manager import StateManager, atomic_write_json, atomic_write_text
from config_validator import validate_config
from utils import (
    get_source_text, get_total_chapters, 
    count_source_chars, call_api, get_source_title,
    print_progress, get_chapters_list, batch_run
)
from phases import *

from phases import __all__ as _phase_all

# 为了完全兼容，导出所有公共函数
__all__ = [
    # 主入口
    'main',
    
    # 状态管理
    'StateManager',
    'atomic_write_json',
    'atomic_write_text',
    
    # 工具函数
    'validate_config',
    'get_source_text',
    'get_total_chapters',
    'count_source_chars',
    'call_api',
    'get_source_title',
    'print_progress',
    'get_chapters_list',
    'batch_run',
    
    # Phase 函数（从 phases 自动发现）
] + _phase_all


if __name__ == '__main__':
    main()
