"""配置校验：全字段 schema 验证，开箱即炸。"""

import os


# ============================================================
# Schema 定义
# ============================================================

# (字段名, 类型, 必填, 说明)
FIELD_SCHEMA = [
    ("book_name", str, False, '新书名（可选，填 "auto" 则开书后自动生成）'),
    ("author", str, True, "作者名"),
    ("source_book", str, True, "源文书名（目录名）"),
    ("rewrites_dir", str, True, "仿写输出目录（相对或绝对）"),
    ("api_key", str, False, "API密钥（可走环境变量 API_KEY）"),
    ("channel", str, False, "频道: male/female"),
    ("genre", str, False, "品类（自动检测时可空）"),
    ("model", str, False, "写章模型名"),
    ("detect_model", str, False, "品类检测模型名"),
    ("prompts_dir", str, False, "prompt 目录（默认 .agents/skills/fangcun-novel/prompts）"),
    ("base_dir", str, False, "项目根目录（默认 CWD）"),
    ("source_chapter_dir", str, False, "源文章节目录（绝对或相对于 base_dir）"),
    ("batch_size", dict, False, '批大小配置: {"write": 10, "guides": 10}'),
    ("topic", str, False, "强制话题/题材"),
    ("pleasure", str, False, "爽点类型"),
    ("reasoning_effort", str, False, "推理力度: low/medium/high"),
]

REQUIRED_FIELDS = [f[0] for f in FIELD_SCHEMA if f[2]]


def validate_config(config):
    """校验配置完整性，返回错误列表。"""
    errors = []

    # 必填字段
    for key in REQUIRED_FIELDS:
        val = config.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"缺少必填字段: {key}")

    # 类型检查
    for key, expected_type, required, _ in FIELD_SCHEMA:
        val = config.get(key)
        if val is None or val == "":
            continue
        if not isinstance(val, expected_type):
            errors.append(f"字段 {key} 类型错误: 期望 {expected_type.__name__}, 实际 {type(val).__name__}")

    # API Key（仅警告，部分 phase 无需 LLM）
    api_key = config.get("api_key") or os.environ.get("API_KEY")
    if not api_key:
        config["_api_key_missing"] = True  # 标记，供需要 LLM 的 phase 检查

    # channel 枚举
    channel = config.get("channel")
    if channel and channel not in ("male", "female"):
        errors.append(f"channel 必须是 male 或 female，当前: {channel}")

    # reasoning_effort 枚举
    reasoning_effort = config.get("reasoning_effort")
    if reasoning_effort and reasoning_effort not in ("low", "medium", "high"):
        errors.append(f"reasoning_effort 必须是 low/medium/high，当前: {reasoning_effort}")

    # 路径可访问性（非必填字段的路径仅在有值时检查）
    base_dir = config.get("base_dir")
    if base_dir and not os.path.isdir(base_dir):
        errors.append(f"base_dir 不存在: {base_dir}")

    if config.get("prompts_dir"):
        pd = config["prompts_dir"]
        if not pd.startswith("."):
            resolved = os.path.join(base_dir or os.getcwd(), pd) if not os.path.isabs(pd) else pd
            if not os.path.isdir(resolved):
                errors.append(f"prompts_dir 不存在: {resolved}")

    return errors
