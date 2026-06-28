"""
Tool Executor — 方寸写作工具执行器。
Claude 通过此模块调用所有写作工具。

用法:
    from tool_executor import run_tool, init_project

    # 建项目
    init_project("/path/to/project")

    # 执行工具
    result = run_tool("outline-generate", {user_input: "都市 销售逆袭"}, project_dir)
    result = run_tool("write-chapter", {chapter_number: 5}, project_dir)
"""

import os, sys, json, re
from pathlib import Path
from urllib.request import Request, urlopen

# 路径设置
_TOOLS_DIR = Path(__file__).parent
_SHARED_TOOLS = _TOOLS_DIR.parent.parent.parent / "tools"
_PROJECT_ROOT = _TOOLS_DIR.parent.parent.parent.parent

for _p in [str(_TOOLS_DIR), str(_SHARED_TOOLS)]:
    if _p not in sys.path:
        sys.path.insert(0, str(_p))

from variable_resolver import VariableResolver
from source_analysis import extract_events as _extract_events

_BUILTIN_DIR = _TOOLS_DIR / "builtin"


# ─── LLM 调用 ─────────────────────────────────────────────

def call_llm(messages: list, temperature: float = 0.7):
    """调用 LLM。"""
    api_key = os.environ.get("API_KEY", "")
    if not api_key or not api_key.startswith("sk-"):
        api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN", api_key)
    if not api_key:
        return None, "未设置 API_KEY"
    _base = os.environ.get("API_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    if not _base.endswith("/v1"):
        _base += "/v1"
    api_url = _base + "/chat/completions"
    model = os.environ.get("FANGCUN_MODEL", "deepseek-chat")
    body = json.dumps({"model": model, "messages": messages, "temperature": temperature}).encode()
    req = Request(api_url, data=body, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=180) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, str(e)


# ─── 项目初始化 ──────────────────────────────────────────

def init_project(project_dir: str):
    """创建新项目目录结构。"""
    p = Path(project_dir)
    p.mkdir(parents=True, exist_ok=True)
    for d in ["正文/卷纲", "正文/章纲", "正文/正文",
              "作品信息/设定/角色", "作品信息/设定/背景",
              "作品信息/设定/势力", "作品信息/设定/地点",
              "作品信息/设定/物品", "作品信息/主题"]:
        (p / d).mkdir(parents=True, exist_ok=True)


# ─── 文件保存 ─────────────────────────────────────────────

def save_output_files(text: str, project_dir: str) -> list[str]:
    """扫描 `==== path ====` 标记并保存文件。"""
    saved = []
    for m in re.finditer(r'====\s*([^\n=]+)\s*====\s*\n(.*?)(?=\n====|\Z)', text, re.DOTALL):
        path = m.group(1).strip()
        content = m.group(2).strip()
        if not path or not content:
            continue
        fp = Path(project_dir) / path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding='utf-8')
        saved.append(path)
    return saved


# ─── 工具执行 ─────────────────────────────────────────────

_PRESET_ALIAS = {
    "开书": "book-draw", "顶层设计": "book-draw",
    "简介": "synopsis-generate", "总纲": "outline-generate", "标签": "tags-generate",
    "角色生成": "character-generate", "设计角色": "character-generate", "人设": "character-generate",
    "提取角色": "character-extract",
    "卷纲": "volume-outline",
    "章纲": "plot-guide", "细纲": "plot-guide", "生成章纲": "plot-guide",
    "写章": "write-chapter", "续写": "write-chapter",
    "去AI": "deslop", "润色": "deslop",
    "对比": "compare", "审查": "compare",
    "脑洞": "premise-draw",
}

# 单文件工具：无标记时直接保存到预设路径
_SINGLE_FILE_MAP = {
    "synopsis-generate": "作品信息/主题/简介.xml",
    "outline-generate": "作品信息/主题/总纲.xml",
    "tags-generate": "作品信息/主题/标签.xml",
}


def run_tool(preset_name: str, args: dict, project_dir: str) -> str:
    """执行一个写作工具。

    Args:
        preset_name: 预设名（内置工具名，或用户关键词）
        args: 参数字典（user_input, chapter_number 等）
        project_dir: 项目路径

    Returns:
        执行结果描述
    """
    # 别名解析
    preset_name = _PRESET_ALIAS.get(preset_name, preset_name)

    # 建项目（如需要）
    if preset_name in ("book-draw", "synopsis-generate", "outline-generate",
                       "tags-generate", "character-generate", "character-extract",
                       "plot-guide", "volume-outline", "write-chapter"):
        if not Path(project_dir).exists():
            init_project(project_dir)

    # ─── 单文件工具（LLM + 保存）───
    if preset_name in _SINGLE_FILE_MAP:
        return _run_single_file_preset(preset_name, _SINGLE_FILE_MAP[preset_name], args, project_dir)

    # ─── 其他内置工具 ───
    if preset_name == "book-draw":
        return _run_single_file_preset("book-draw", None, args, project_dir)
    elif preset_name == "write-chapter":
        return _run_single_file_preset("write-chapter", None, args, project_dir)
    elif preset_name == "plot-guide":
        return _run_single_file_preset("plot-guide", None, args, project_dir)
    elif preset_name == "volume-outline":
        return _run_single_file_preset("volume-outline", None, args, project_dir)
    elif preset_name == "character-generate":
        return _run_single_file_preset("character-generate", None, args, project_dir)
    elif preset_name == "character-extract":
        # 优先用 Python 并行提取（快），source_dir 为空时降级到 XML prompt
        source_dir = args.get("source_dir", "")
        if source_dir:
            return _run_extract_events(args, project_dir)
        return _run_single_file_preset("character-extract", None, args, project_dir)
    elif preset_name == "premise-draw":
        return _run_single_file_preset("premise-draw", None, args, project_dir)
    elif preset_name == "book-import":
        return _run_single_file_preset("book-import", None, args, project_dir)
    elif preset_name == "skeleton":
        return _run_single_file_preset("skeleton", None, args, project_dir)
    elif preset_name == "style-analysis":
        return _run_single_file_preset("style-analysis", None, args, project_dir)
    elif preset_name == "adaptation":
        return _run_single_file_preset("adaptation", None, args, project_dir)
    else:
        return f"未知工具: {preset_name}"


def _run_single_file_preset(preset_name: str, save_path: str | None, args: dict, project_dir: str) -> str:
    """加载预设→LLM→保存（通用）。"""
    import xml.etree.ElementTree as ET
    preset_file = _BUILTIN_DIR / f"{preset_name}.xml"
    if not preset_file.exists():
        return f"预设 {preset_name} 不存在"
    try:
        tree = ET.parse(preset_file)
        sp_raw = tree.getroot().findtext("prompt", "")
    except Exception:
        return f"预设 {preset_name} 解析失败"

    resolver = VariableResolver(project_dir)
    resolver.set_context(
        N=args.get("chapter_number", args.get("ch", 1)),
        total_chapters=args.get("total_chapters", ""),
        start=args.get("start", 1),
        end=args.get("end", 1),
    )
    # 非保留参数 → 变量覆盖
    _reserved = {"chapter_number", "ch", "user_input", "message", "story_name", "total_chapters", "start", "end"}
    overrides = {k: v for k, v in args.items() if k not in _reserved and isinstance(v, str)}
    if overrides:
        resolver.set_user_overrides(overrides)
    sp = resolver.render(sp_raw)
    user_msg = args.get("user_input", args.get("message", ""))
    messages = [{"role": "system", "content": sp}]
    if user_msg:
        messages.append({"role": "user", "content": user_msg})

    resp, err = call_llm(messages)
    if err:
        return f"LLM 调用失败: {err}"
    if not resp:
        return "LLM 返回空"

    saved = save_output_files(resp, project_dir)
    if not saved:
        if save_path:
            fp = Path(project_dir) / save_path
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(resp, encoding='utf-8')
            saved = [save_path]
        elif preset_name == "volume-outline":
            # 卷纲落笔：从内容提取卷号（兼容 XML 和 Markdown 格式）
            vol_id = re.search(r'<volume\s+id="(\d+)"', resp) or re.search(r'第(\d+)卷', resp)
            vol_name = re.search(r'name="([^"]+)"', resp) or re.search(r'卷名[：:]\s*([^\n]+)', resp)
            vol_tag = f"第{vol_id.group(1)}卷" if vol_id else "卷纲"
            vol_suffix = f"_{vol_name.group(1)}" if vol_name else ""
            vol_suffix = re.sub(r'[\\/:*?"<>|\s]', '', vol_suffix)  # 去非法字符
            fn = f"{vol_tag}{vol_suffix}.xml"
            fp = Path(project_dir) / "正文" / "卷纲" / fn
            fp.parent.mkdir(parents=True, exist_ok=True)
            # 清理 markdown 包裹
            clean = re.sub(r'```(?:xml)?\n?', '', resp).strip()
            fp.write_text(clean, encoding='utf-8')
            saved = [f"正文/卷纲/{fn}"]
        elif preset_name == "write-chapter":
            m = re.search(r'第(\d+)', args.get("user_input", "") + str(args.get("ch", "")))
            ch = m.group(1) if m else args.get("ch", 1)
            fp = Path(project_dir) / f"正文/正文/第{ch}章.xml"
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(resp, encoding='utf-8')
            saved = [f"正文/正文/第{ch}章.xml"]
        elif preset_name == "character-generate":
            # 角色落笔：从响应中提取角色名
            name_m = re.search(r'name="([^"]+)"', resp)
            if name_m:
                fp = Path(project_dir) / "作品信息" / "设定" / "角色" / f"{name_m.group(1)}.xml"
                fp.parent.mkdir(parents=True, exist_ok=True)
                import xml.etree.ElementTree as ET
                # 清理 markdown 包裹
                clean = re.sub(r'```(?:xml)?\n?', '', resp).strip()
                fp.write_text(clean, encoding='utf-8')
                saved = [f"作品信息/设定/角色/{name_m.group(1)}.xml"]
    return f"{preset_name} 完成: 保存 {len(saved)} 个文件"


def _run_extract_events(args: dict, project_dir: str) -> str:
    """提取事件表（仿写链）。"""
    source_dir = args.get("source_dir", project_dir)
    config = {
        "project_dir": project_dir,
        "source_dir": source_dir,
        "model": args.get("model", "deepseek-chat"),
    }
    api_key = os.environ.get("API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
    _base = os.environ.get("API_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    if not _base.endswith("/v1"): _base += "/v1"
    api_url = _base + "/chat/completions"
    model = config["model"]
    prompt_text = "提取事件表"
    workers = args.get("workers", 5)
    events = _extract_events(config, api_key, api_url, model, prompt_text, workers)
    if not events:
        return "事件提取失败"
    return f"事件提取完成: {len(events)} 章"
