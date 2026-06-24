"""Phase 模块：各个 pipeline 阶段的实现。"""

from phases.compare import phase_compare
from phases.extract import phase_extract
from phases.guides import phase_guides
from phases.open_book import phase_prep, phase_source_analysis, phase_open_book
from phases.postprocess import phase_postfix, phase_trim, phase_rewrite, phase_polish, phase_expand
from phases.style_extract import phase_style_extract
from phases.validate import phase_validate, validate_one
from phases.write import phase_write
from phases.write_agent import phase_write_agent

__all__ = [k for k in dir() if k.startswith("phase_") or k == "validate_one"]
