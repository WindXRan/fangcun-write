"""
writer-engine: 通用写作流水线

接受 prompt 文件路径 + context，执行：加载 prompt → 注入 context → 调 LLM → 校验 → 保存。
"""

import re
import json
from pathlib import Path
from datetime import datetime

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def list_prompts():
    """列出所有可用的 prompt 模板。"""
    prompts = []
    for p in sorted(PROMPTS_DIR.rglob("*.md")):
        rel = p.relative_to(PROMPTS_DIR)
        prompts.append(str(rel))
    return prompts


def load_prompt(prompt_path: str) -> str:
    """加载 prompt 模板。支持相对路径和绝对路径。"""
    p = Path(prompt_path)
    if p.is_absolute() and p.exists():
        return p.read_text(encoding="utf-8")
    # 相对于 prompts/ 目录
    full = PROMPTS_DIR / prompt_path
    if full.exists():
        return full.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt 不存在: {prompt_path}")


def inject_context(prompt: str, context: dict) -> str:
    """将 context 中的变量注入 prompt 模板。"""
    for key, value in context.items():
        if isinstance(value, str):
            prompt = prompt.replace(f"{{{key}}}", value)
        elif isinstance(value, (int, float)):
            prompt = prompt.replace(f"{{{key}}}", str(value))
    return prompt


def validate_output(output: str, rules: dict = None) -> list[str]:
    """校验输出质量。返回问题列表，空=合格。"""
    if not rules:
        return []

    issues = []

    # 字数校验
    if "字数" in rules:
        min_w, max_w = rules["字数"]
        chars = len(re.sub(r'\s', '', output))
        if chars < min_w:
            issues.append(f"字数不足: {chars} < {min_w}")
        elif chars > max_w:
            issues.append(f"字数超标: {chars} > {max_w}")

    # 禁用词校验
    if "禁用词" in rules:
        for word in rules["禁用词"]:
            if word in output:
                issues.append(f"包含禁用词: {word}")

    # 角色名校验
    if "禁止源文名" in rules:
        for name in rules["禁止源文名"]:
            if name in output:
                issues.append(f"包含源文角色名: {name}")

    # △ 标记校验（剧本专用）
    if rules.get("必须有△"):
        if "△" not in output:
            issues.append("缺少△场景描述标记")

    # XML 标签校验
    if rules.get("必须有scriptItem"):
        if "<scriptItem" not in output:
            issues.append("缺少<scriptItem>标签")

    return issues


def auto_fix(output: str, issues: list[str], rules: dict = None) -> str:
    """自动修复简单问题。"""
    # 替换源文角色名
    if rules and "替换角色名" in rules:
        for old, new in rules["替换角色名"].items():
            output = output.replace(old, new)

    # 去掉尾部元数据
    output = re.sub(r'\n*【字数[：:]\s*\d+\s*字?】\s*$', '', output)

    return output


def execute(
    prompt: str,
    context: dict = None,
    rules: dict = None,
    output_path: str = None,
    system_prompt: str = None,
    api_key: str = None,
    api_url: str = None,
    model: str = "deepseek-chat",
    temperature: float = 0.8,
    max_tokens: int = 4096,
) -> dict:
    """
    执行一次写作任务。

    Args:
        prompt: prompt 模板路径（如 "novel/imitation/write.md"）
        context: 注入 prompt 的变量字典
        rules: 校验规则
        output_path: 输出文件路径
        system_prompt: 系统提示词（可选）
        api_key: API key
        api_url: API URL
        model: 模型名
        temperature: 温度
        max_tokens: 最大 token 数

    Returns:
        {"output": str, "issues": list, "saved": str}
    """
    # 1. 加载 prompt
    prompt_template = load_prompt(prompt)

    # 2. 注入 context
    if context:
        user_prompt = inject_context(prompt_template, context)
    else:
        user_prompt = prompt_template

    # 3. 调 LLM
    _ensure_path()
    from lib.api_client import call_api

    output = call_api(
        api_key=api_key,
        model=model,
        user_prompt=user_prompt,
        system_prompt=system_prompt or "",
        api_url=api_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # 4. 校验
    issues = validate_output(output, rules)

    # 5. 自动修复
    if issues and rules:
        output = auto_fix(output, issues, rules)
        # 重新校验
        issues = validate_output(output, rules)

    # 6. 保存
    saved_path = None
    if output_path and not issues:
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(output, encoding="utf-8")
        saved_path = str(p)

    return {
        "output": output,
        "issues": issues,
        "saved": saved_path,
        "chars": len(re.sub(r'\s', '', output)),
    }


def write_chapter(config: dict, ch_num: int, mode: str = "imitation") -> dict:
    """
    高层写章接口。自动选择 prompt + 组装 context + 调 LLM + 校验 + 保存。

    Args:
        config: 项目配置
        ch_num: 章节号
        mode: "imitation"（仿写）或 "continue"（续写）

    Returns:
        {"output": str, "issues": list, "saved": str, "chars": int}
    """
    _ensure_path()
    from file_io import (
        get_source_text, load_characters, load_plot_guide,
        load_style_text, load_chapter, get_rewrites_dir,
    )

    rewrites_dir = str(get_rewrites_dir(config))
    api_key = config.get("api_key") or os.environ.get("API_KEY", "")
    api_url = config.get("api_base_url") or os.environ.get("API_BASE_URL", "")
    model = config.get("model", "deepseek-chat")

    # 1. 选择 prompt
    prompt_path = _resolve_prompt(mode)

    # 2. 组装 context
    context = _build_context(config, ch_num, mode)

    # 3. 校验规则
    rules = _build_rules(config, mode)

    # 4. 输出路径
    output_path = str(Path(rewrites_dir) / "chapters" / f"ch_{ch_num:03d}.txt")

    # 5. 执行
    return execute(
        prompt=prompt_path,
        context=context,
        rules=rules,
        output_path=output_path,
        system_prompt=config.get("system_prompt", ""),
        api_key=api_key,
        api_url=api_url,
        model=model,
        temperature=config.get("temperature", 0.8),
        max_tokens=config.get("max_tokens", 4096),
    )


def _resolve_prompt(mode: str) -> str:
    """根据 mode 选择 prompt 文件路径。"""
    # 先找 mode 特定的 write.md
    mode_prompt = PROMPTS_DIR / mode / "write.md"
    if mode_prompt.exists():
        return str(mode_prompt)
    # fallback: 通用 write.md
    generic = PROMPTS_DIR / "write.md"
    if generic.exists():
        return str(generic)
    raise FileNotFoundError(f"找不到 prompt: {mode}/write.md 或 write.md")


def _build_context(config: dict, ch_num: int, mode: str) -> dict:
    """根据 mode 组装 context 变量。"""
    _ensure_path()
    from file_io import (
        get_source_text, load_characters, load_plot_guide,
        load_style_text, load_chapter, get_rewrites_dir,
        get_chapter_event, get_skeleton_context, get_adaptation_principles,
    )

    rewrites_dir = str(get_rewrites_dir(config))
    context = {
        "N": str(ch_num),
        "N03d": f"{ch_num:03d}",
        "新书名": config.get("book_name", ""),
        "作者名": config.get("author", ""),
        "源书名": config.get("source_book", ""),
    }

    if mode == "imitation":
        # 仿写模式：需要源文参照
        src = get_source_text(config, ch_num)
        context["源文全文"] = src or ""
        context["源文字数"] = str(len(re.sub(r'\s', '', src))) if src else "0"

        plot = load_plot_guide(config, ch_num)
        context["章纲"] = plot or ""

        style = load_style_text(config, ch_num)
        context["文笔指纹"] = style or ""

        chars = load_characters(config)
        context["角色卡"] = chars or ""

        context["本章事件"] = get_chapter_event(config, ch_num) or ""
        context["全局结构"] = get_skeleton_context(config, ch_num) or ""
        context["改写原则"] = get_adaptation_principles(config) or ""

        # 上一章
        prev = load_chapter(config, ch_num - 1) if ch_num > 1 else ""
        context["前文"] = prev or ""

    elif mode == "continue":
        # 续写模式：无源文，靠前文延续
        chars = load_characters(config)
        context["角色卡"] = chars or ""

        plot = load_plot_guide(config, ch_num)
        context["章纲"] = plot or ""

        # 上一章
        prev = load_chapter(config, ch_num - 1) if ch_num > 1 else ""
        context["前文"] = prev or ""

        context["源文全文"] = ""
        context["文笔指纹"] = ""
        context["本章事件"] = ""
        context["全局结构"] = ""
        context["改写原则"] = ""

    return context


def _build_rules(config: dict, mode: str) -> dict:
    """根据 mode 构建校验规则。"""
    rules = {
        "字数": (2000, 3000),
    }

    # 仿写模式：禁止源文角色名
    if mode == "imitation":
        _ensure_path()
        from file_io import load_characters
        chars = load_characters(config)
        if chars:
            # 提取源文角色名
            source_names = []
            for m in re.finditer(r'【(.+?)】[（(]源文对应[：:](.+?)[）)]', chars):
                old_names = re.split(r'[/、]', m.group(2))
                for n in old_names:
                    n = n.strip()
                    if n and n != m.group(1).strip():
                        source_names.append(n)
            if source_names:
                rules["禁止源文名"] = source_names

    return rules


def _ensure_path():
    """确保 lib/ 在 path 中。"""
    import sys
    lib_dir = Path(__file__).parent.parent.parent / "source-engine" / "tools"
    if str(lib_dir) not in sys.path:
        sys.path.insert(0, str(lib_dir))
    lib_sub = lib_dir / "lib"
    if str(lib_sub) not in sys.path:
        sys.path.insert(0, str(lib_sub))


def _get_api_config(config):
    """从配置中获取API参数"""
    api_key = config.get("api_key") or os.environ.get("API_KEY", "")
    api_url = config.get("api_base_url") or os.environ.get("API_BASE_URL", "")
    model = config.get("model", "deepseek-chat")
    return api_key, api_url, model


def trim_chapter(config, ch_num, mode="imitation"):
    """精简章节"""
    _ensure_path()
    from file_io import load_chapter, get_rewrites_dir
    
    rewrites_dir = str(get_rewrites_dir(config))
    ch_file = Path(rewrites_dir) / "chapters" / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        print(f"    [ERROR] 章节不存在: {ch_file}")
        return None
    
    original = ch_file.read_text(encoding="utf-8")
    target_chars = int(len(original.replace(" ", "").replace("\n", "")) * 0.8)
    
    # 加载prompt
    prompt_path = PROMPTS_DIR / mode / "trim.md"
    if not prompt_path.exists():
        prompt_path = PROMPTS_DIR / "trim.md"
    
    prompt_template = load_prompt(str(prompt_path))
    context = {
        "content": original,
        "target_chars": str(target_chars),
    }
    prompt = inject_context(prompt_template, context)
    
    api_key, api_url, model = _get_api_config(config)
    
    try:
        result = execute(
            prompt=prompt,
            output_path=str(ch_file),
            system_prompt="你是一个专业的小说编辑，擅长精简文字。",
            api_key=api_key,
            api_url=api_url,
            model=model,
            max_tokens=int(target_chars * 2),
        )
        return result.get("output")
    except Exception as e:
        print(f"    [ERROR] 精简失败: {e}")
        return None


def polish_chapter(config, ch_num, mode="imitation"):
    """润色章节"""
    _ensure_path()
    from file_io import load_chapter, get_rewrites_dir
    
    rewrites_dir = str(get_rewrites_dir(config))
    ch_file = Path(rewrites_dir) / "chapters" / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        print(f"    [ERROR] 章节不存在: {ch_file}")
        return None
    
    original = ch_file.read_text(encoding="utf-8")
    original_chars = len(original.replace(" ", "").replace("\n", ""))
    
    # 加载prompt
    prompt_path = PROMPTS_DIR / mode / "polish.md"
    if not prompt_path.exists():
        prompt_path = PROMPTS_DIR / "polish.md"
    
    prompt_template = load_prompt(str(prompt_path))
    context = {
        "content": original,
        "min_chars": str(int(original_chars * 0.9)),
        "max_chars": str(int(original_chars * 1.1)),
    }
    prompt = inject_context(prompt_template, context)
    
    api_key, api_url, model = _get_api_config(config)
    
    try:
        result = execute(
            prompt=prompt,
            output_path=str(ch_file),
            system_prompt="你是一个专业的小说编辑，擅长润色文笔。",
            api_key=api_key,
            api_url=api_url,
            model=model,
            max_tokens=int(original_chars * 1.5),
        )
        return result.get("output")
    except Exception as e:
        print(f"    [ERROR] 润色失败: {e}")
        return None


def expand_chapter(config, ch_num, mode="imitation", target_chars=None):
    """扩写章节"""
    _ensure_path()
    from file_io import load_chapter, get_rewrites_dir
    
    rewrites_dir = str(get_rewrites_dir(config))
    ch_file = Path(rewrites_dir) / "chapters" / f"ch_{ch_num:03d}.txt"
    
    if not ch_file.exists():
        print(f"    [ERROR] 章节不存在: {ch_file}")
        return None
    
    original = ch_file.read_text(encoding="utf-8")
    original_chars = len(original.replace(" ", "").replace("\n", ""))
    
    if target_chars is None:
        target_chars = int(original_chars * 1.3)
    
    # 加载prompt
    prompt_path = PROMPTS_DIR / mode / "expand.md"
    if not prompt_path.exists():
        prompt_path = PROMPTS_DIR / "expand.md"
    
    prompt_template = load_prompt(str(prompt_path))
    context = {
        "content": original,
        "orig_chars": str(original_chars),
        "target_chars": str(target_chars),
    }
    prompt = inject_context(prompt_template, context)
    
    api_key, api_url, model = _get_api_config(config)
    
    try:
        result = execute(
            prompt=prompt,
            output_path=str(ch_file),
            system_prompt="你是一个专业的小说写手，擅长扩写。",
            api_key=api_key,
            api_url=api_url,
            model=model,
            max_tokens=int(target_chars * 1.5),
        )
        return result.get("output")
    except Exception as e:
        print(f"    [ERROR] 扩写失败: {e}")
        return None


def rewrite_chapter(config, ch_num, mode="imitation", reason=""):
    """重写章节"""
    _ensure_path()
    from file_io import load_chapter, get_rewrites_dir
    
    rewrites_dir = str(get_rewrites_dir(config))
    
    # 加载prompt
    prompt_path = PROMPTS_DIR / mode / "rewrite.md"
    if not prompt_path.exists():
        prompt_path = PROMPTS_DIR / "rewrite.md"
    
    prompt_template = load_prompt(str(prompt_path))
    context = _build_context(config, ch_num, mode)
    context["reason"] = reason or "（无具体原因，整章重写）"
    prompt = inject_context(prompt_template, context)
    
    api_key, api_url, model = _get_api_config(config)
    
    output_path = str(Path(rewrites_dir) / "chapters" / f"ch_{ch_num:03d}.txt")
    
    try:
        result = execute(
            prompt=prompt,
            output_path=output_path,
            system_prompt="你是一个专业的小说写手。重写时必须解决上述问题，保持角色一致性。",
            api_key=api_key,
            api_url=api_url,
            model=model,
            max_tokens=4096,
        )
        return result.get("output")
    except Exception as e:
        print(f"    [ERROR] 重写失败: {e}")
        return None
