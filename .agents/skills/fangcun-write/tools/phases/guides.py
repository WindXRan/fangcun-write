"""Phase 2: plot-guide 生成（已拆分为子模块）。

本文件保留为兼容入口，实际逻辑分布在：
- guides_cache.py  — 缓存管理、数据加载
- guides_name.py   — 名称映射、角色解析
- guides_world.py  — 世界观、概念、风格类型
- guides_style.py  — 文笔指纹、高光提取
- guides_main.py   — 主流程、run_one、phase_guides
"""

# 从子模块导入所有公开接口（保持向后兼容）
from guides_cache import (
    _get_system_prompt_cached,
    _load_skeleton_map,
    _get_source_text_for_chapter,
    _get_source_chars_for_chapter,
    _get_book_data,
    _load_events_mapped,
    _load_skeleton_mapped,
    _load_adaptation_mapped,
)

from guides_name import (
    _build_name_map,
    _build_name_map_text,
    _extract_gender_info,
    _build_name_list,
    _get_chapter_characters,
    _load_character_cards,
    _load_char_card,
)

from guides_world import (
    _get_world_text,
    _get_world_constraint,
    _get_genre_text,
    _load_avatar_knowledge,
    _get_blacklist_text,
)

from guides_style import (
    _get_style_fingerprint,
    _get_style_text_mapped,
    _extract_highlights,
    get_source_metrics,
)

from guides_main import (
    phase_guides,
    run_one,
    run_one_with_template,
    process_plot_guide_output,
    _strip_source_text,
    _extract_info_release,
    _is_continue_mode,
    _get_continue_plan_event,
    _get_continue_style,
)
