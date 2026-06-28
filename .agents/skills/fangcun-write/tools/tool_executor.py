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

import os, sys, json, re, traceback
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
    model = os.environ.get("FANGCUN_MODEL", "deepseek-v4-pro")
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
    """扫描输出标记并保存文件。支持两种格式（优先 XML，降级 ====）：

    XML 格式:
      <output>
        <file path="相对路径">
          (文件内容)
        </file>
      </output>

    旧格式:
      ==== path ====
      content
      ==== next_path ====
    """
    import xml.etree.ElementTree as ET
    saved = []

    # 1. 尝试 XML 格式：<output [tool="..."]><file path="...">content</file></output>
    # 用正则而非 XML 解析，避免文件内容中的特殊字符破坏解析
    xml_match = re.search(r'<output[^>]*>(.*?)</output>', text, re.DOTALL)
    if xml_match:
        for m in re.finditer(r'<file\s+path="([^"]+)"\s*>(.*?)</file>', xml_match.group(1), re.DOTALL):
            path = m.group(1).strip()
            content = m.group(2).strip()
            if path and content:
                fp = Path(project_dir) / path
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(content, encoding='utf-8')
                saved.append(path)
        if saved:
            return saved

    # 2. 降级：旧 ==== path ==== 格式
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
    "开书": "book-draw", "顶层设计": "book-draw", "原创开书": "book-draw",
    "仿写开书": "open-book", "开书全套": "open-book",
    "简介": "synopsis-generate", "总纲": "outline-generate", "标签": "tags-generate",
    "角色生成": "character-generate", "设计角色": "character-generate", "人设": "character-generate",
    "提取角色": "character-extract",
    "卷纲": "volume-outline",
    "章纲": "plot-guide-nanpin", "细纲": "plot-guide-nanpin", "生成章纲": "plot-guide-nanpin",
    "男频章纲": "plot-guide-nanpin", "女频章纲": "plot-guide-nvpin",
    "写章": "write-chapter", "续写": "write-chapter",
    "去AI": "deslop", "润色": "deslop",
    "对比": "compare", "审查": "compare",
    "脑洞": "premise-draw",
    "选卡": "apply-pick", "应用": "apply-pick",
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

    elif preset_name == "plot-guide-nanpin":
        return _run_single_file_preset("plot-guide-nanpin", None, args, project_dir)
    elif preset_name == "plot-guide-nvpin":
        return _run_single_file_preset("plot-guide-nvpin", None, args, project_dir)
    elif preset_name == "volume-outline":
        return _run_single_file_preset("volume-outline", None, args, project_dir)
    elif preset_name == "character-generate":
        return _run_single_file_preset("character-generate", None, args, project_dir)
    elif preset_name == "character-extract":
        return _run_single_file_preset("character-extract", None, args, project_dir)
    elif preset_name == "premise-draw":
        return _run_single_file_preset("premise-draw", None, args, project_dir)
    elif preset_name == "apply-pick":
        return _apply_pick(project_dir, args)
    elif preset_name == "open-book":
        return _run_single_file_preset("open-book", None, args, project_dir)
    elif preset_name == "book-import":
        return _run_single_file_preset("book-import", None, args, project_dir)
    elif preset_name == "book-import-raw":
        # 原始小说导入：需要 source（源路径）参数
        source = args.get("source", "")
        if not source:
            return "缺少 source 参数（源文件/目录路径）"
        from importer import run_import
        result = run_import(
            book_name=args.get("book_name", project_dir.split("/")[-1] if "/" in project_dir else project_dir),
            author=args.get("author", ""),
            source=source,
            channel=args.get("channel", "男频"),
            project_dir=project_dir,
        )
        if result["success"]:
            return (f"✓ 导入完成：{result['book_name']}（{result['author']}）\n"
                    f"  {result['total_chapters']} 章 → {result['project_dir']}")
        return f"✗ 导入失败: {result.get('error', '未知错误')}"
    elif preset_name == "skeleton":
        return _run_single_file_preset("skeleton", None, args, project_dir)
    elif preset_name == "style-analysis":
        return _run_single_file_preset("style-analysis", None, args, project_dir)
    elif preset_name == "adaptation":
        return _run_single_file_preset("adaptation", None, args, project_dir)
    else:
        return f"未知工具: {preset_name}"


def _inject_tool_attribute(xml_path: str, tool_name: str):
    """在 XML 文件根元素添加 tool 属性（如已有则跳过）。"""
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        if root.get("tool") is None:
            root.set("tool", tool_name)
            tree.write(xml_path, encoding='utf-8', xml_declaration=False)
    except Exception:
        pass  # 非标准 XML 或解析失败，不报错


def _run_single_file_preset(preset_name: str, save_path: str | None, args: dict, project_dir: str) -> str:
    """加载预设→LLM→保存（通用）。支持 rounds 参数抽卡。"""
    import xml.etree.ElementTree as ET
    preset_file = _BUILTIN_DIR / f"{preset_name}.xml"
    if not preset_file.exists():
        return f"预设 {preset_name} 不存在"
    try:
        tree = ET.parse(preset_file)
        sp_raw = tree.getroot().findtext("prompt", "")
    except Exception as _ex:
        traceback.print_exc()
        return f"预设 {preset_name} 解析失败: {_ex}"

    rounds = int(args.get("rounds", 1))
    # 抽卡模式：跑多轮，每轮结果存抽卡文件，用户选一个应用
    if rounds > 1:
        return _run_multi_round(preset_name, save_path, args, project_dir, sp_raw)

    resolver = VariableResolver(project_dir)
    resolver.set_context(
        N=args.get("chapter_number", args.get("ch", 1)),
        volume=args.get("volume_number", args.get("vol", "")),
        total_chapters=args.get("total_chapters", ""),
        start=args.get("start", 1),
        end=args.get("end", 1),
    )
    # 非保留参数 → 变量覆盖
    _reserved = {"chapter_number", "ch", "volume_number", "vol", "user_input", "message", "story_name", "total_chapters", "start", "end"}
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
        # 兜底：没有 ==== 标记时，根据工具类型自动确定保存路径
        _FALLBACK_PATHS = {
            "book-import": "作品信息/主题/总纲.xml",
            "synopsis-generate": "作品信息/主题/简介.xml",
            "outline-generate": "作品信息/主题/总纲.xml",
            "tags-generate": "作品信息/主题/标签.xml",
            "skeleton": "故事骨架.md",
            "adaptation": "改编策略.md",
            "plot-guide": f"正文/章纲/第{args.get('chapter_number', 1)}章.xml",
            "plot-guide-nanpin": f"正文/章纲/第{args.get('chapter_number', 1)}章.xml",
            "plot-guide-nvpin": f"正文/章纲/第{args.get('chapter_number', 1)}章.xml",
            "write-chapter": f"正文/正文/第{args.get('chapter_number', 1)}章.xml",
            "volume-outline": "正文/卷纲/卷纲.xml",
            "character-generate": "作品信息/设定/角色.xml",
        }
        fallback = _FALLBACK_PATHS.get(preset_name, save_path)
        if fallback:
            fp = Path(project_dir) / fallback
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(resp, encoding='utf-8')
            saved = [fallback]
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
    # 在所有 XML 文件根元素注入 tool 属性
    for path in saved:
        fp = Path(project_dir) / path
        if fp.suffix.lower() == ".xml":
            _inject_tool_attribute(str(fp), preset_name)
    return f"{preset_name} 完成: 保存 {len(saved)} 个文件"



# ─── 抽卡模式：多轮生成 → 用户选一 ─────────────────


def _run_multi_round(preset_name: str, save_path: str | None,
                     args: dict, project_dir: str, sp_raw: str) -> str:
    """跑 N 轮抽卡，每轮结果存 .抽卡{N} 文件，返回菜单供用户挑选。"""
    import xml.etree.ElementTree as ET
    rounds = int(args.get("rounds", 5))
    temperature_base = float(args.get("temperature", 0.8))

    ch = args.get("chapter_number", args.get("ch", 1))
    _FALLBACK_PATHS = {
        "book-import": "作品信息/主题/总纲.xml",
        "synopsis-generate": "作品信息/主题/简介.xml",
        "outline-generate": "作品信息/主题/总纲.xml",
        "tags-generate": "作品信息/主题/标签.xml",
        "skeleton": "故事骨架.md",
        "adaptation": "改编策略.md",
        "plot-guide": f"正文/章纲/第{ch}章.xml",
        "plot-guide-nanpin": f"正文/章纲/第{ch}章.xml",
        "plot-guide-nvpin": f"正文/章纲/第{ch}章.xml",
        "write-chapter": f"正文/正文/第{ch}章.xml",
        "volume-outline": "正文/卷纲/卷纲.xml",
        "character-generate": "作品信息/设定/角色.xml",
        "premise-draw": None,
    }
    base_path = save_path or _FALLBACK_PATHS.get(preset_name)
    if not base_path:
        return f"抽卡模式暂不支持 {preset_name}（未配置基准保存路径）"

    base_file = Path(project_dir) / base_path
    stem = base_file.stem
    ext = base_file.suffix

    results = []
    for r in range(1, rounds + 1):
        t = min(1.5, max(0.1, temperature_base + (r - 1) * 0.05))

        resolver = VariableResolver(project_dir)
        resolver.set_context(
            N=ch,
            volume=args.get("volume_number", args.get("vol", "")),
            total_chapters=args.get("total_chapters", ""),
            start=args.get("start", 1),
            end=args.get("end", 1),
        )
        _reserved = {"chapter_number", "ch", "volume_number", "vol", "user_input",
                     "message", "story_name", "total_chapters", "start", "end", "rounds", "round"}
        overrides = {k: v for k, v in args.items() if k not in _reserved and isinstance(v, str)}
        if overrides:
            resolver.set_user_overrides(overrides)
        sp = resolver.render(sp_raw)
        user_msg = args.get("user_input", args.get("message", ""))
        messages = [{"role": "system", "content": sp}]
        if user_msg:
            messages.append({"role": "user", "content": user_msg})

        resp, err = call_llm(messages)
        if err or not resp:
            results.append((r, None, f"LLM 失败: {err or '空响应'}"))
            continue

        card_file = base_file.parent / f"{stem}.抽卡{r}{ext}"
        card_file.parent.mkdir(parents=True, exist_ok=True)
        card_file.write_text(resp, encoding='utf-8')

        preview_lines = resp.strip().split('\n')[:3]
        preview = " | ".join(l.strip()[:40] for l in preview_lines if l.strip())
        if len(preview) > 120:
            preview = preview[:120] + "..."

        results.append((r, str(card_file), preview))

    lines = [f"\n{'='*60}", f"  {preset_name} × {rounds} 轮抽卡完成", f"{'='*60}"]
    for r, path, preview in results:
        status = f"→ {path}" if path else f"✗ {preview}"
        lines.append(f"\n  [{r}] {status}")
        if preview and path:
            lines.append(f"     预览: {preview[:80]}")

    lines.append(f"\n  运行「选卡 N」应用第 N 轮结果到正式文件")
    return "\n".join(lines)


def _apply_pick(project_dir: str, args: dict) -> str:
    """用户选中的抽卡结果 → 复制为正式文件。"""
    import glob

    round_num = args.get("round")
    if not round_num:
        return "缺少 round 参数，示例：选卡 3"

    cards = sorted(Path(project_dir).rglob(f"*.抽卡{round_num}.*"))
    if not cards:
        return f"未找到 .抽卡{round_num} 文件"

    picked = cards[0]
    stem = picked.stem
    base_stem = stem.rsplit(".抽卡", 1)[0] if ".抽卡" in stem else stem
    target = picked.parent / f"{base_stem}{picked.suffix}"

    content = picked.read_text(encoding='utf-8')
    target.write_text(content, encoding='utf-8')

    for card in sorted(Path(project_dir).rglob("*.抽卡*.*")):
        try:
            card.unlink()
        except:
            pass

    return (f"✓ 已应用 [{round_num}] → {target}")
