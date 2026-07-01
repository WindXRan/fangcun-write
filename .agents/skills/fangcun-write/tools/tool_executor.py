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

from llm_provider import call_llm
from file_utils import init_project, save_output_files, _inject_tool_attribute

_PRESET_ALIAS = {
    "开书": "book-draw", "顶层设计": "book-draw", "原创开书": "book-draw",
    "仿写开书": "open-book", "开书全套": "open-book",
    "拆书": "pipeline-import", "逆推": "pipeline-import",
    "提取摘要": "chapter-summary",
    "黄金开篇": "golden-opening", "黄金三章": "golden-chapters",
    "简介": "synopsis-generate", "总纲": "outline-generate", "标签": "tags-generate",
    "角色生成": "character-generate", "设计角色": "character-generate", "人设": "character-generate",
    "提取角色": "character-extract",
    "角色深度": "character-deep",
    "提取设定": "setting-extract",
    "关系图谱": "relationship-extract",
    "卷纲": "volume-outline",
    "章纲": "plot-guide-nanpin", "细纲": "plot-guide-nanpin", "生成章纲": "plot-guide-nanpin",
    "男频章纲": "plot-guide-nanpin", "女频章纲": "plot-guide-nvpin",
    "写章": "write-chapter", "续写": "write-chapter",
    "去AI": "deslop", "润色": "deslop",
    "对比": "compare", "审查": "compare",
    "脑洞": "premise-draw",
    "选卡": "apply-pick", "应用": "apply-pick",
    "导入拆解": "pipeline-import",
    "运 pipeline": "pipeline-run",
    "source-guide": "source-guide-reverse", "章纲逆推": "source-guide-reverse",
    "guide-convert": "guide-convert", "章纲转换": "guide-convert",
    "仿写章节": "write-chapter", "fanxie-chapter": "write-chapter",
    "仿写管线": "imitation", "仿写批量": "imitation-batch", "批量仿写": "imitation-batch",
}

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
    
    # ── 自动缓冲区：source-guide-reverse 领先写章10章 ──
    if preset_name in ("write-chapter", "guide-convert"):
        ch = args.get("chapter_number", args.get("ch", 1))
        import os as _os, glob as _glob
        from pathlib import Path as _Path
        # 计算已逆推章数
        # 从 project.xml 读取源文项目名
        import xml.etree.ElementTree as _ET
        _px = _Path(project_dir) / "作品信息" / "project.xml"
        _src_book = ""
        if _px.exists():
            try: _src_book = (_ET.parse(str(_px)).getroot().findtext("source_book") or "").strip()
            except: pass
        if not _src_book:
            raise ValueError(f"{project_dir}/project.xml 未设置 source_book，无法定位源文项目")
        _src_dir = _Path(project_dir).parent / _src_book
        guide_dir = _src_dir / "正文" / "章纲"
        existing_guides = len(list(guide_dir.glob("第*.xml"))) if guide_dir.exists() else 0
        # 如果逆推落后于写章+10章，自动补一批
        if existing_guides < ch + 10:
            need = ch + 15
            _run_tool_silent = lambda n: _run_single_file_preset("source-guide-reverse", None, {"chapter_number": n}, str(_src_dir))
            for n in range(existing_guides + 1, need + 1):
                p = guide_dir / f"第{n}章.xml"
                if p.exists(): continue
                print(f"  [auto] 逆推第{n}章...", flush=True)
                _run_tool_silent(n)
            print(f"  [auto] 缓冲区已扩充到第{need}章", flush=True)

    # 女频自动路由：章纲生成默认走女频版
    if preset_name in ("plot-guide", "plot-guide-nanpin"):
        proj_xml = Path(project_dir) / "作品信息" / "project.xml"
        if proj_xml.exists():
            try:
                import xml.etree.ElementTree as ET
                pt = ET.parse(str(proj_xml))
                channel = (pt.getroot().findtext("channel") or "").strip()
                if channel == "女频":
                    preset_name = "plot-guide-nvpin"
            except Exception:
                pass

    # 建项目（如需要）
    if preset_name in ("book-draw", "synopsis-generate", "outline-generate",
                       "tags-generate", "character-generate", "character-extract",
                       "plot-guide", "volume-outline", "write-chapter",
                       "open-book", "pattern-analysis"):
        if not Path(project_dir).exists():
            init_project(project_dir,
                       story_name=args.get("story_name", ""),
                       channel=args.get("channel", "男频"))

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
    elif preset_name == "source-guide":
        return _run_single_file_preset("source-guide", None, args, project_dir)
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
    elif preset_name in ("仿写管线", "imitation"):
        return _run_imitation_chapter(args, project_dir)
    elif preset_name in ("仿写批量", "imitation-batch", "批量仿写"):
        return _run_imitation_batch(args, project_dir)
    elif preset_name == "open-book":
        return _run_single_file_preset("open-book", None, args, project_dir)
    elif preset_name == "book-import":
        return _run_single_file_preset("book-import", None, args, project_dir)
    elif preset_name == "pipeline-import":
        return _run_pipeline_import(args, project_dir)
    elif preset_name == "book-import-raw":

        # 原始小说导入：需要 source（源路径）参数
        source = args.get("source", "")
        if not source:
            return "缺少 source 参数（源文件/目录路径）"
        from importer import run_import
        result = run_import(
        book_name=args.get("book_name", Path(project_dir).name),
            author=args.get("author", ""),
            source=source,
            channel=args.get("channel", "男频"),
            project_dir=project_dir,
        )
        if not result["success"]:
            return f"✗ 导入失败: {result.get('error', '未知错误')}"

        msg = "✓ 导入完成：" + result["book_name"] + "（" + result["author"] + "）"
        msg += "\n  " + str(result["total_chapters"]) + " 章 → " + result["project_dir"]

        # 有 API key 时自动走逆推 pipeline
        if os.environ.get("API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            out_dir = result["project_dir"]
            from pipeline_import import step_pattern_analysis, step_book_import, step_volume_outline
            msg += "\n  API 就绪，自动逆推..."
            step_pattern_analysis(out_dir)
            step_book_import(out_dir, result["book_name"], result["total_chapters"])
            step_volume_outline(out_dir)
            msg += "\n  ✓ 逆推总纲/简介/标签/卷纲/套路 已生成"
        else:
            msg += "\n  ⚠ 未设置 API_KEY，跳过逆推（后续可跑「导入拆解」补全）"

        return msg
    elif preset_name == "skeleton":
        return _run_single_file_preset("skeleton", None, args, project_dir)
    elif preset_name == "style-analysis":
        return _run_single_file_preset("style-analysis", None, args, project_dir)
    elif preset_name == "adaptation":
        return _run_single_file_preset("adaptation", None, args, project_dir)
    elif preset_name == "pipeline-run":
        from pipeline_runner import run_pipeline as _run_pipeline
        p_name = args.get("pipeline", args.get("name", ""))
        if not p_name:
            return "缺少 pipeline 名称"
        return _run_pipeline(p_name, args, project_dir)
    elif preset_name == "chapter-summary":
        from chapter_summary import extract_all
        result = extract_all(project_dir)
        if result:
            total = len(result)
            ok = sum(1 for r in result if "核心事件" in r)
            return f"摘要提取完成: {ok}/{total} 章"
        return "摘要提取失败: 无数据"
    elif preset_name == "character-deep":
        return _run_single_file_preset("character-deep", None, args, project_dir)
    elif preset_name == "setting-extract":
        return _run_single_file_preset("setting-extract", None, args, project_dir)
    elif preset_name == "relationship-extract":
        return _run_single_file_preset("relationship-extract", None, args, project_dir)
    else:
        # 兜底：尝试作为预设加载（支持子目录工具）
        return _run_single_file_preset(preset_name, None, args, project_dir)


def _run_single_file_preset(preset_name: str, save_path: str | None, args: dict, project_dir: str) -> str:
    """加载预设→LLM→保存（通用）。支持 rounds 参数抽卡。"""
    preset_file_md = _BUILTIN_DIR / f"{preset_name}.md"
    preset_file_xml = _BUILTIN_DIR / f"{preset_name}.xml"
    if not preset_file_md.exists() and not preset_file_xml.exists():
        for subdir in sorted(_BUILTIN_DIR.iterdir()):
            if subdir.is_dir():
                candidate_md = subdir / f"{preset_name}.md"
                if candidate_md.exists():
                    preset_file_md = candidate_md
                    break
                candidate_xml = subdir / f"{preset_name}.xml"
                if candidate_xml.exists():
                    preset_file_xml = candidate_xml
                    break
    sp_raw = ""
    if preset_file_md.exists():
        try:
            md_text = preset_file_md.read_text(encoding='utf-8')
            if md_text.startswith('---'):
                parts = md_text.split('---', 2)
                sp_raw = parts[2].strip() if len(parts) >= 3 else md_text
            else:
                sp_raw = md_text
        except Exception as _ex:
            traceback.print_exc()
            return f"预设 {preset_name}.md 解析失败: {_ex}"
    elif preset_file_xml.exists():
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(preset_file_xml)
            sp_raw = tree.getroot().findtext("prompt", "")
        except Exception as _ex:
            traceback.print_exc()
            return f"预设 {preset_name}.xml 解析失败: {_ex}"
    else:
        return f"预设 {preset_name} 不存在"

    # 读取仿写项目中的 source_book（源文路径）
    proj_xml = Path(project_dir) / "作品信息" / "project.xml"
    source_book = ""
    source_dir = ""
    if proj_xml.exists():
        try:
            pt = ET.parse(proj_xml)
            pr = pt.getroot()
            source_book = (pr.findtext("source_book") or "").strip()
            source_author = (pr.findtext("author") or "").strip()
            if source_book:
                sb_dir = Path(project_dir).parent / source_book
                if sb_dir.exists():
                    source_dir = str(sb_dir / "正文" / "正文")
                # 也尝试 拆文库/{source_book}/
                chaifen = Path(project_dir).parent.parent / "拆文库" / source_book
                if not source_dir and chaifen.exists():
                    source_dir = str(chaifen)
        except Exception:
            pass
    # Fix 3: 如果 args 传了 source_book 但 project.xml 没有，自动写入
    if not source_book:
        sb_from_args = args.get("source_book", "").strip()
        if sb_from_args:
            source_book = sb_from_args
            try:
                import xml.etree.ElementTree as ET2
                pt2 = ET2.parse(proj_xml)
                pr2 = pt2.getroot()
                sb_el = pr2.find("source_book")
                if sb_el is None:
                    sb_el = ET2.SubElement(pr2, "source_book")
                sb_el.text = source_book
                pt2.write(proj_xml, encoding='utf-8', xml_declaration=True)
            except Exception:
                pass

    rounds = int(args.get("rounds", 1))
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
    # 设置源文信息（仿写模式使用）
    if source_book:
        resolver.set_user_overrides({"source_book": source_book})
    if source_dir:
        resolver.set_source_dir(source_dir)
    # 非保留参数 → 变量覆盖
    _reserved = {"chapter_number", "ch", "volume_number", "vol", "user_input", "message", "story_name", "total_chapters", "start", "end"}
    overrides = {k: v for k, v in args.items() if k not in _reserved and isinstance(v, str)}
    if overrides:
        resolver.set_user_overrides(overrides)
    sp = resolver.render(sp_raw)
    # 🛡️ P0 安全检查：检测 prompt 中的变量解析失败标记
    _fail_markers = re.findall(r'@\[解析失败:[^\]]+\]|@\[未定义:[^\]]+\]|@\[未找到:[^\]]+\]', sp)
    if _fail_markers:
        _marker_str = "; ".join(_fail_markers[:5])
        print(f"  [⚠️ P0] prompt 包含 {len(_fail_markers)} 处变量解析失败: {_marker_str}")
        # 不终止，但把失败变量名收集起来，附加到 prompt 末尾提醒 LLM 忽略
        _warn = f"\n\n# ⚠️ 系统提示\n以下变量解析失败，请忽略它们，不要尝试使用或补全：\n"
        for m in _fail_markers:
            _warn += f"- {m}\n"
        sp = sp + _warn
    # debug: 保存渲染后的完整 prompt 到 _debug/ 目录
    try:
        import datetime
        _debug_dir = Path(project_dir) / "_debug"
        _debug_dir.mkdir(exist_ok=True)
        _ch = args.get("chapter_number", args.get("ch", ""))
        _ts = datetime.datetime.now().strftime("%H%M%S")
        _fn = f"{_ts}_{preset_name}_ch{_ch}.txt"
        _debug_file = _debug_dir / _fn
        # 头部：调用信息
        _header = (
            f"# tool: {preset_name}\n"
            f"# time: {datetime.datetime.now().isoformat()}\n"
            f"# chapter: {_ch}\n"
            f"# story: {args.get('story_name', '')}\n"
            f"# args: { {k:v for k,v in args.items() if k not in ('user_input',)} }\n"
            f"{'='*60}\n"
        )
        _debug_file.write_text(_header + sp, encoding='utf-8')
        print(f"  [debug] prompt → {_debug_file}")
    except Exception as _ex:
        try:
            (_debug_dir / "_error.log").write_text(str(_ex), encoding='utf-8')
        except Exception:
            pass
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
            "source-guide": f"正文/章纲/第{args.get('chapter_number', 1)}章.xml",
            "write-chapter": f"正文/正文/第{args.get('chapter_number', 1)}章.xml",
            "volume-outline": f"正文/卷纲/第{args.get("volume_number", args.get("vol", 1))}卷.xml",
            "character-generate": "作品信息/设定/角色.xml",
            "source-guide-reverse": f"正文/章纲/第{args.get('chapter_number', 1)}章.xml",
            "guide-convert": f"正文/章纲/第{args.get('chapter_number', 1)}章.xml",
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



def _run_imitation_chapter(args: dict, project_dir: str) -> str:
    """仿写管线：一条命令写一章。自动跑 source-guide-reverse → guide-convert → write-chapter。"""
    import time, re
    from pathlib import Path

    ch = args.get("chapter_number", args.get("ch", 1))
    src = args.get("source_book", "")

    # 找源文项目
    if not src:
        px = Path(project_dir) / "作品信息" / "project.xml"
        if px.exists():
            import xml.etree.ElementTree as ET
            src = (ET.parse(str(px)).getroot().findtext("source_book") or "").strip()
    if not src:
        raise ValueError(f"{project_dir}/project.xml 未设置 source_book，无法定位源文项目")

    src_dir = str(Path(project_dir).parent / src)
    if not Path(src_dir).exists():
        return f"源文项目 {src} 不存在"

    msgs = []

    # Step 1: source-guide-reverse
    try:
        run_tool("source-guide-reverse", {"chapter_number": ch}, src_dir)
        msgs.append(f"源文章纲✅")
    except Exception as e:
        msgs.append(f"源文章纲❌{str(e)[:40]}")

    try:
        run_tool("guide-convert", {"chapter_number": ch}, project_dir)
        msgs.append(f"新文章纲✅")
    except Exception as e:
        msgs.append(f"新文章纲❌{str(e)[:40]}")

    # Step 3: write-chapter（带下一章章纲参考）
    _wc_args = {"chapter_number": ch}
    _next_guide = Path(project_dir) / "正文" / "章纲" / f"第{ch+1}章.xml"
    if _next_guide.exists():
        _ng_text = _next_guide.read_text(encoding='utf-8')
        import xml.etree.ElementTree as _ng_et
        try:
            _ng_root = _ng_et.fromstring(_ng_text)
            _ng_core = _ng_root.findtext("core_event", "")[:100]
            _ng_title = _ng_root.findtext("chapter_title", "")
            if _ng_core:
                _wc_args["user_input"] = f"下一章提要：{_ng_title} — {_ng_core}"
        except:
            pass
    try:
        r = run_tool("write-chapter", _wc_args, project_dir)
        # Check output
        out = Path(project_dir) / "正文" / "正文" / f"第{ch}章.xml"
        if out.exists():
            text = out.read_text(encoding='utf-8')
            m = re.search(r'<content>(.*?)</content>', text, re.DOTALL)
            content = m.group(1).strip() if m else text.strip()
            wc = len(content)
            # Fix wrapper
            if '<content>' not in text and content:
                wrapped = f'<chapter number="{ch}" tool="write-chapter">\n  <content>\n{content}\n  </content>\n</chapter>'
                out.write_text(wrapped, encoding='utf-8')
            msgs.append(f"正文✅{wc}字")
        else:
            msgs.append(f"正文❌无文件")
    except Exception as e:
        msgs.append(f"正文❌{str(e)[:40]}")

    # 伏笔追踪：从章纲提取未解决的冲突/预言/新角色
    try:
        guide_path = Path(project_dir) / "正文" / "章纲" / f"第{ch}章.xml"
        if guide_path.exists():
            guide_text = guide_path.read_text(encoding='utf-8')
            import json as _json
            tracker_path = Path(project_dir) / "作品信息" / "设定" / "plot_tracker.json"
            threads = _json.loads(tracker_path.read_text(encoding='utf-8')) if tracker_path.exists() else []

            # 从章纲的 info_hold 和 hooks 提取伏笔
            holds = _re.findall(r'<info_hold>([^<]+)</info_hold>', guide_text)
            hooks = _re.findall(r'<cliffhanger>([^<]+)</cliffhanger>', guide_text)

            new_threads = []
            for h in holds[:3]:  # 最多记3条
                new_threads.append({"ch": ch, "thread": h.strip()[:150], "status": "open"})
            for h in hooks[:1]:
                new_threads.append({"ch": ch, "thread": h.strip()[:150], "status": "open"})

            if new_threads:
                threads.extend(new_threads)
                tracker_path.write_text(_json.dumps(threads, ensure_ascii=False, indent=2), encoding='utf-8')
                msgs.append(f"伏笔{len(new_threads)}条")
    except Exception:
        pass

    return f"第{ch}章: {' | '.join(msgs)}"


def _run_imitation_batch(args: dict, project_dir: str) -> str:
    """仿写批量：并行跑 source-guide-reverse + guide-convert → 串行 write-chapter。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    from pathlib import Path

    start = int(args.get("start", args.get("chapter_number", 1)))
    end = int(args.get("end", args.get("last", 50)))
    src_book = args.get("source_book", "")
    if not src_book:
        import xml.etree.ElementTree as _ET2
        _px2 = Path(project_dir) / "作品信息" / "project.xml"
        if _px2.exists():
            try: src_book = (_ET2.parse(str(_px2)).getroot().findtext("source_book") or "").strip()
            except: pass
    if not src_book:
        raise ValueError(f"{project_dir}/project.xml 未设置 source_book，无法定位源文项目")
    src_dir = str(Path(project_dir).parent / src_book)
    concurrency = int(args.get("workers", 5))

    chapters = list(range(start, end + 1))
    lines = []
    _total_start = time.time()

    # Phase 1: parallel source-guide-reverse
    t0 = time.time()
    lines.append(f"Phase 1: source-guide-reverse {start}-{end} ({concurrency}并发)")
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(run_tool, "source-guide-reverse", {"chapter_number": ch}, src_dir): ch for ch in chapters}
        for f in as_completed(futs):
            ch = futs[f]
            try:
                f.result()
                lines.append(f"  源文{ch}✅")
            except:
                lines.append(f"  源文{ch}❌")
    lines.append(f"  Phase 1耗时: {time.time()-t0:.0f}s")

    # Phase 2: parallel guide-convert
    t0 = time.time()
    lines.append(f"Phase 2: guide-convert {start}-{end} ({concurrency}并发)")
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(run_tool, "guide-convert", {"chapter_number": ch}, project_dir): ch for ch in chapters}
        for f in as_completed(futs):
            ch = futs[f]
            try:
                f.result()
                lines.append(f"  转换{ch}✅")
            except:
                lines.append(f"  转换{ch}❌")
    lines.append(f"  Phase 2耗时: {time.time()-t0:.0f}s")

    # Phase 3: sequential write-chapter
    t0 = time.time()
    lines.append(f"Phase 3: write-chapter {start}-{end} (串行)")
    for ch in chapters:
        t1 = time.time()
        try:
            r = run_tool("write-chapter", {"chapter_number": ch}, project_dir)
            out = Path(project_dir) / "正文" / "正文" / f"第{ch}章.xml"
            if out.exists():
                text = out.read_text(encoding='utf-8')
                import re
                m = re.search(r'<content>(.*?)</content>', text, re.DOTALL)
                content = m.group(1).strip() if m else text.strip()
                wc = len(content)
                lines.append(f"  ch{ch}: ✅{wc}字 {time.time()-t1:.0f}s")
            else:
                lines.append(f"  ch{ch}: ❌无文件")
        except Exception as e:
            lines.append(f"  ch{ch}: ❌{str(e)[:40]}")
    lines.append(f"  Phase 3耗时: {time.time()-t0:.0f}s")

    lines.append(f"总耗时: {time.time()-_total_start:.0f}s")
    return "\n".join(lines)


def _run_pipeline_import(args: dict, project_dir: str) -> str:
    """导入+拆解管线。"""
    source = args.get("source", "")
    if not source:
        return "缺少 source 参数"
    from pipeline_import import run_pipeline
    success = run_pipeline(
        book_name=args.get("book_name", Path(project_dir).name),
        author=args.get("author", ""),
        source=source,
        channel=args.get("channel", "男频"),
        project_dir=project_dir,
    )
    return f"✓ 导入拆解完成" if success else f"✗ 导入拆解失败"

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
        "source-guide": f"正文/章纲/第{ch}章.xml",
        "write-chapter": f"正文/正文/第{ch}章.xml",
        "volume-outline": f"正文/卷纲/第{args.get("volume_number", args.get("vol", 1))}卷.xml",
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
        # 仿写模式：设置源文信息
        _px = Path(project_dir) / "作品信息" / "project.xml"
        if _px.exists():
            try:
                _pt = ET.parse(_px)
                _pr = _pt.getroot()
                _sb = (_pr.findtext("source_book") or "").strip()
                if _sb:
                    resolver.set_user_overrides({"source_book": _sb})
            except Exception:
                pass
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
