"""
VariableResolver 计算处理器。注册所有 COMPUTED_HANDLERS。
"""
import re, json
from pathlib import Path
from variable_resolver import VariableResolver



VariableResolver.COMPUTED_HANDLERS["current_chapter"] = (
    lambda self: str(self._ctx("N", "?"))
)
VariableResolver.COMPUTED_HANDLERS["current_volume"] = (
    lambda self: str(self._ctx("volume", "?"))
)
VariableResolver.COMPUTED_HANDLERS["target_words"] = (
    VariableResolver._compute_target_words
)
VariableResolver.COMPUTED_HANDLERS["target_words_min"] = (
    VariableResolver._compute_target_words_min
)
VariableResolver.COMPUTED_HANDLERS["target_words_max"] = (
    VariableResolver._compute_target_words_max
)
VariableResolver.COMPUTED_HANDLERS["total_chapters"] = (
    lambda self: str(self._ctx("total_chapters", "?"))
)

# ── 角色名：读第一个角色文件 ——─────────────────────────
def _protagonist_name(self, fallback: str) -> str:
    """找主角：优先 project.xml <protagonist> → role=protagonist → 第一个角色卡。"""
    import xml.etree.ElementTree as ET
    # 1. 从 project.xml 读取
    _px = self.novel_dir / "作品信息" / "project.xml"
    if _px.exists():
        try:
            _pr = ET.parse(str(_px)).getroot()
            _pn = _pr.findtext("protagonist", "").strip()
            if _pn:
                return _pn
        except: pass
    # 2. 从角色卡扫描
    d = self.novel_dir / "作品信息" / "设定" / "角色"
    if d.exists():
        import re as _re
        for f in sorted(d.glob("*.xml")):
            try:
                text = f.read_text(encoding="utf-8")
                clean = _re.sub(r'```(?:xml)?\n?', '', text).strip()
                clean = _re.sub(r'^.*?(<[a-zA-Z_])', r'\1', clean, flags=_re.DOTALL)
                root = ET.fromstring(clean)
                if root.tag in ("entry", "character"):
                    name = root.get("name", "")
                    if root.get("role", "") == "protagonist":
                        return name
                    if fallback == "主角":
                        fallback = name
            except: pass
    return fallback

VariableResolver.COMPUTED_HANDLERS["protagonist_name"] = (
    lambda self: _protagonist_name(self, "主角")
)
VariableResolver.COMPUTED_HANDLERS["源文换皮"] = (
    lambda self: self._user_overrides.get("源文对照", "")
)
VariableResolver.COMPUTED_HANDLERS["关联章节"] = (
    lambda self: _prev_chapter_tail(self)
)
VariableResolver.COMPUTED_HANDLERS["关联章纲"] = (
    lambda self: _prev_chapter_guide(self)
)
# 旧名兼容

# 本章正文：读取当前章节的正文文件
def _current_chapter_text(self):
    """当前章节正文。"""
    N = self._ctx("N", 1)
    import re
    # 精确匹配
    for ext in ("", ".xml"):
        p = self.novel_dir / "正文" / "正文" / f"第{N}章{ext}"
        if p.exists():
            text = p.read_text(encoding="utf-8")
            clean = re.sub(r'<[^>]+>', '', text).strip()
            return clean
    # glob 模糊匹配（兼容 "第1章带着功德投胎了.xml" 这类命名）
    for f in sorted(self.novel_dir.glob(f"正文/正文/第{N}章*.xml")):
        text = f.read_text(encoding="utf-8")
        clean = re.sub(r'<[^>]+>', '', text).strip()
        return clean
    return "（无本章正文）"

VariableResolver.COMPUTED_HANDLERS["本章正文"] = _current_chapter_text

def _prev_chapter_tail(self, tail_chars=300):
    """前文尾段：上一章最后 tail_chars 字（默认300），够接上钩子就行。"""
    N = self._ctx("N", 1)
    if N <= 1: return "（无前文）"
    import re
    for ext in ("", ".xml"):
        p = self.novel_dir / "正文" / "正文" / f"第{N-1}章{ext}"
        if p.exists():
            text = p.read_text(encoding="utf-8")
            clean = re.sub(r'<[^>]+>', '', text).strip()
            tail = clean[-tail_chars:] if len(clean) > tail_chars else clean
            return f"---上一章章尾---\n{tail}"
        # glob
        for f in sorted(self.novel_dir.glob(f"正文/正文/第{N-1}章*.xml")):
            text = f.read_text(encoding="utf-8")
            clean = re.sub(r'<[^>]+>', '', text).strip()
            tail = clean[-tail_chars:] if len(clean) > tail_chars else clean
            return f"---上一章章尾---\n{tail}"
    return "（无前文）"

def _prev_chapter_guide(self, limit=5):
    """最近最多 limit 章的章纲全文。"""
    N = self._ctx("N", 1)
    if N <= 1: return "（无关联章纲）"
    parts = []
    start = max(1, N - limit)
    for i in range(start, N):
        for ext in ("", ".xml"):
            p = self.novel_dir / "正文" / "章纲" / f"第{i}章{ext}"
            if p.exists():
                parts.append(f"---第{i}章章纲---\n{_simplify_xml(p.read_text(encoding='utf-8'))}")
                break
    return "\n\n".join(parts) if parts else "（无关联章纲）"

# ── 本章章纲：读取当前章节的章纲文件 ──
def _current_chapter_guide(self):
    N = self._ctx("N", 1)
    for ext in ("", ".xml"):
        p = self.novel_dir / "正文" / "章纲" / f"第{N}章{ext}"
        if p.exists():
            return p.read_text(encoding="utf-8")
    return f"（错误：第{N}章章纲不存在。请先通过 plot-guide 生成章纲）"

VariableResolver.COMPUTED_HANDLERS["本章章纲"] = _current_chapter_guide

def _chapter_characters(self):
    """从章纲 <characters> 字段读取本章出场角色，只返回对应角色卡。"""
    import re as _re
    N = self._ctx("N", 1)
    # 读章纲
    guide_text = ""
    for ext in ("", ".xml"):
        p = self.novel_dir / "正文" / "章纲" / f"第{N}章{ext}"
        if p.exists():
            guide_text = p.read_text(encoding="utf-8")
            break
    if not guide_text:
        return f"（错误：第{N}章章纲不存在。请先通过 plot-guide 生成章纲）"

    # 提取 <characters> 字段（兼容两种格式）
    m = _re.search(r'<characters>(.*?)</characters>', guide_text, _re.DOTALL)
    if not m:
        return "（章纲中未标记出场角色）"
    raw = m.group(1).strip()
    # 尝试从 <character name="名"> 属性提取
    xml_names = _re.findall(r'<character\s+name="([^"]+)"', raw)
    if xml_names:
        names = xml_names
    else:
        # 降级：逗号/顿号/空格分隔的纯文本格式
        names = _re.split(r'[、，,\s]+', raw)
        names = [n.strip() for n in names if n.strip() and '角色' not in n]

    # 查找对应角色卡
    chars_dir = self.novel_dir / "作品信息" / "设定" / "角色"
    if not chars_dir.exists():
        return "（角色卡目录不存在）"

    cards = []
    for name in names:
        found = False
        for f in sorted(chars_dir.glob("*.xml")):
            if f.stem == name:
                cards.append(f.read_text(encoding="utf-8"))
                found = True
                break
        if not found:
            cards.append(f"<!-- {name}：未找到角色卡 -->")
    return "\n".join(cards) if cards else "（无匹配角色卡）"

VariableResolver.COMPUTED_HANDLERS["关联角色"] = (
    lambda self: _chapter_characters(self)
)
VariableResolver.COMPUTED_HANDLERS["chapter_characters"] = VariableResolver.COMPUTED_HANDLERS["关联角色"]

# ── 角色列表：列出所有可用角色名（不依赖章纲，供 plot-guide 使用）──
def _all_character_names(self):
    chars_dir = self.novel_dir / "作品信息" / "设定" / "角色"
    if chars_dir.exists():
        names = [f.stem for f in sorted(chars_dir.glob("*.xml"))]
        return f"可用角色：{'、'.join(names)}" if names else "（无角色卡）"
    return "（无角色目录）"

VariableResolver.COMPUTED_HANDLERS["角色列表"] = _all_character_names
VariableResolver.COMPUTED_HANDLERS["antagonist_name"] = (
    lambda self: _first_char_name(self, "对手")
)
VariableResolver.COMPUTED_HANDLERS["ally_name"] = (
    lambda self: _first_char_name(self, "引路人")
)
def _chapter_summaries(self):
    """读取全书章节摘要JSON，格式化为LLM易读文本。"""
    f = self.novel_dir / "作品信息" / "章节摘要.json"
    if not f.exists():
        return "（无章节摘要，请先运行摘要提取）"
    try:
        import json
        data = json.loads(f.read_text(encoding='utf-8'))
        from chapter_summary import format_summaries
        return format_summaries(data)
    except Exception as e:
        return f"（章节摘要读取失败: {e}）"

VariableResolver.COMPUTED_HANDLERS["chapter_summaries"] = _chapter_summaries


# ── 仿写变量：自动从源文目录解析 ──

def _source_chapter(self):
    """从源文项目读取当前章节正文。三步：source_dir → 同级目录 → 拆文库。"""
    import os as _os
    N = self._ctx("N", 1)
    
    # 优先从 project.xml 读 source_book（比 _user_overrides 更可靠）
    _sb = ""
    try:
        _px = self.novel_dir / "作品信息" / "project.xml"
        if _px.exists():
            import xml.etree.ElementTree as _ET
            _sb = (_ET.parse(str(_px)).getroot().findtext("source_book") or "").strip()
    except Exception:
        pass
    if not _sb:
        _sb = self._user_overrides.get("source_book", "")
    
    # 直接从源文目录读文件
    if _sb:
        try:
            _parent = self.novel_dir.parent
            _src_dir = _os.path.join(str(_parent), _sb, "正文", "正文")
            if _os.path.isdir(_src_dir):
                _candidates = []
                for _f in _os.listdir(_src_dir):
                    if f"第{N}章" in _f and (_f.endswith(".xml") or _f.endswith(".txt")):
                        if "_humanized" not in _f and "_repair" not in _f and "_polish" not in _f:
                            _candidates.append(_f)
                # 优先选文件名最长的（原文通常带章名如"第1章带着功德投胎了.xml"，
                # 我们的输出是"第1章.xml"）
                if _candidates:
                    _candidates.sort(key=len, reverse=True)
                    with open(_os.path.join(_src_dir, _candidates[0]), 'r', encoding='utf-8', errors='replace') as _fh:
                        return _fh.read()
        except Exception:
            pass
    
    source_book = self._user_overrides.get("source_book", "")
    if not source_book:
        return ""

    # 从用户覆盖中取
    manual = self._user_overrides.get("源文对照", "")
    if manual:
        return manual

    import os as _os

    # 尝试所有可能的源文目录
    novel_dir = self.novel_dir
    candidates = []

    # 1. source_dir（tool_executor 设定的标准入口）
    sd = self._ctx("source_dir", "")
    if sd:
        candidates.append(sd)

    # 2. 同级目录：{project}/../{source_book}/正文/正文/
    candidates.append(str(novel_dir.parent / source_book / "正文" / "正文"))

    # 3. 同级目录：{project}/../{source_book}/源文/
    candidates.append(str(novel_dir.parent / source_book / "源文"))

    # 4. 拆文库
    candidates.append(str(novel_dir.parent.parent / "拆文库" / source_book / "正文" / "正文"))
    candidates.append(str(novel_dir.parent.parent / "拆文库" / source_book / "源文"))

    # 5. 同级目录直接文件
    candidates.append(str(novel_dir.parent / source_book))

    # 遍历所有候选目录，用 os.listdir 避免 Path.glob 的 Unicode 问题
    seen = set()
    for cd in candidates:
        if not cd or cd in seen:
            continue
        seen.add(cd)
        if not _os.path.isdir(cd):
            continue
        try:
            fnames = []
            for fn in _os.listdir(cd):
                if f"第{N}章" in fn and (fn.endswith(".xml") or fn.endswith(".txt") or fn.endswith(".md")):
                    fnames.append(fn)
            # 优先长文件名（带标题的原文件），短名（纯"第N章.xml"为输出文件）靠后
            fnames.sort(key=lambda x: len(x), reverse=True)
            for fname in fnames:
                fp = _os.path.join(cd, fname)
                with open(fp, 'r', encoding='utf-8', errors='replace') as fh:
                    return fh.read()
        except Exception:
            continue
    return ""

VariableResolver.COMPUTED_HANDLERS["源文对照"] = _source_chapter


# ── 源文卷纲：从源文项目读取卷纲 ──
def _source_volume(self):
    """从源文项目读取当前卷的卷纲。"""
    import os as _os
    vol = self._ctx("volume", 1)
    # 直接从源文目录读
    try:
        _novel = self.novel_dir
        _parent = _novel.parent
        _src_dir = _os.path.join(str(_parent), "全家偷听心声", "正文", "卷纲")
        if not _os.path.isdir(_src_dir):
            # 从 project.xml 读 source_book
            _px = _novel / "作品信息" / "project.xml"
            if _px.exists():
                import xml.etree.ElementTree as _ET
                _sb = (_ET.parse(str(_px)).getroot().findtext("source_book") or "").strip()
                if _sb:
                    _src_dir = _os.path.join(str(_parent), _sb, "正文", "卷纲")
        if _os.path.isdir(_src_dir):
            for _f in _os.listdir(_src_dir):
                if f"第{vol}卷" in _f and (_f.endswith(".xml") or _f.endswith(".txt")):
                    with open(_os.path.join(_src_dir, _f), 'r', encoding='utf-8', errors='replace') as _fh:
                        return _fh.read()
    except Exception:
        pass
    return "（无源文卷纲）"

VariableResolver.COMPUTED_HANDLERS["源文卷纲"] = _source_volume


# ── 源文章纲：从源文项目读取完整章纲（供 guide-convert 翻译使用）──
def _source_chapter_guide(self):
    """从源文项目读取当前章纲的完整内容。"""
    import os as _os
    N = self._ctx("N", 1)
    try:
        _novel = self.novel_dir
        _parent = _novel.parent
        _src_dir = _os.path.join(str(_parent), "全家偷听心声", "正文", "章纲")
        if not _os.path.isdir(_src_dir):
            _px = _novel / "作品信息" / "project.xml"
            if _px.exists():
                import xml.etree.ElementTree as _ET
                _sb = (_ET.parse(str(_px)).getroot().findtext("source_book") or "").strip()
                if _sb:
                    _src_dir = _os.path.join(str(_parent), _sb, "正文", "章纲")
        if _os.path.isdir(_src_dir):
            for _f in sorted(_os.listdir(_src_dir)):
                if f"第{N}章" in _f and (_f.endswith(".xml") or _f.endswith(".txt")):
                    with open(_os.path.join(_src_dir, _f), 'r', encoding='utf-8', errors='replace') as _fh:
                        return _fh.read()
            for _f in sorted(_os.listdir(_src_dir)):
                if f"{N}" in _f and (_f.endswith(".xml") or _f.endswith(".txt")):
                    with open(_os.path.join(_src_dir, _f), 'r', encoding='utf-8', errors='replace') as _fh:
                        return _fh.read()
    except Exception:
        pass
    return "（无源文章纲，请先对源文项目运行 source-guide-reverse）"

VariableResolver.COMPUTED_HANDLERS["源文章纲"] = _source_chapter_guide




def _fmt_tag(m):
    """<tag attr="x">inner</tag> → tag: inner（内层有标签时展平为子项）"""
    tag = m.group(1).split()[0]
    inner = m.group(2).strip()
    # 内层有标签时递归
    return tag + ':\n' + _indent(inner) if '<' in inner else tag + ': ' + inner


def _indent(text):
    """给多行文本加缩进"""
    return '\n'.join('  ' + l for l in text.split('\n'))


def _attrs_to_kv(m):
    """<tag a="x" b="y"> → a: x, b: y"""
    attrs = re.findall(r"([a-zA-Z_]+)=([^\s>]+)", m.group(2))
    return ', '.join(f'{k}: {v.strip(chr(34)+chr(39))}' for k, v in attrs)


def _simplify_xml(raw: str) -> str:
    """剥掉 XML 标签，保留内容。标签名转为行首标签。"""
    # 剥声明和注释
    raw = re.sub(r'<\?xml[^>]*\?>', '', raw)
    raw = re.sub(r'<!--.*?-->', '', raw, flags=re.DOTALL)
    # 自闭合标签: <tag a="x" b="y" /> → a: x, b: y
    raw = re.sub(r'<([a-zA-Z_][^>]*?)\s+([^>]+?)\s*/>', _attrs_to_kv, raw)
    # 无属性的自闭合标签: <tag /> → 删除
    raw = re.sub(r'<[a-zA-Z_][^>]*/>', '', raw)
    # <tag>text</tag> → tag: text（不嵌套）
    prev = None
    while prev != raw:
        prev = raw
        raw = re.sub(r'<([a-zA-Z_][^>]*)>(.*?)<\/\1>', _fmt_tag, raw, flags=re.DOTALL)
    # 清理残余标签
    raw = re.sub(r'<[^>]+>', '', raw)
    # 清理空行和首尾空格
    lines = [l.strip() for l in raw.split('\n') if l.strip()]
    return '\n'.join(lines)


# ─── 套路分析精简器：仿写模式只提取节奏节点和情绪 ───

def _extract_rhythm(raw: str) -> str:
    """从套路分析 XML 中只提取节奏节点和情绪模板，去掉其他模块。"""
    import re
    parts = []
    # 提取 rhythm_nodes 区块
    m = re.search(r'<rhythm_nodes>(.*?)</rhythm_nodes>', raw, re.DOTALL)
    if m:
        nodes = _simplify_xml(m.group(0))
        parts.append('【节奏节点】\n' + nodes)
    # 提取 emotional_template
    m = re.search(r'<emotional_template>(.*?)</emotional_template>', raw, re.DOTALL)
    if m:
        et = _simplify_xml(m.group(0))
        parts.append('【情绪模板】\n' + et)
    # 提取 genre 定位
    m = re.search(r'<genre[^>]*>(.*?)<\/genre>', raw, re.DOTALL)
    if m:
        parts.append('题材: ' + _simplify_xml(m.group(1)))
    return '\n\n'.join(parts) if parts else _simplify_xml(raw)



def _fanxie_mode(self):

    """仿写模式标志。非空 = 仿写模式生效，空 = 原创模式。"""
    source_book = self._user_overrides.get("source_book", "")
    if source_book:
        return "开启"
    return ""

VariableResolver.COMPUTED_HANDLERS["fanxie_mode"] = _fanxie_mode


def _channel_mode(self):
    """根据频道返回对应模式的内容。"""
    channel = self._user_overrides.get("channel", "")
    channel = channel or self._extract_value({"from": "作品信息/project.xml", "method": "xpath", "xpath": ".//channel"})
    if "女频" in channel:
        return (
            "【女频模式】\n"
            "- 情绪驱动：每个情节都要问读者此刻什么感受（甜/虐/爽/急/酸）\n"
            "- 关系变化：本章至少推进或动摇一段人际关系\n"
            "- 细节渲染：关键情绪点用感官细节放大，不直述\n"
            "- 打脸节奏：打脸前有足够憋屈铺垫"
        )
    return (
        "【男频模式】\n"
        "- 主角驱动：主角必须是主动方，哪怕被动局面也要在段内转化为反击/布局\n"
        "- 冲突密度：每段都有可感知的冲突，不写纯过渡\n"
        "- 升级感：本章结束时主角状态/资源/认知相比章初有可量化的变化\n"
        "- 信息差：善用读者知道而角色不知道的信息制造紧张感"
    )

VariableResolver.COMPUTED_HANDLERS["频道模式"] = _channel_mode


def _source_pattern_analysis(self):
    """从源文目录读取套路分析，不存在则从仿写项目读取。"""
    source_book = self._user_overrides.get("source_book", "")
    if source_book:
        novel_dir = self.novel_dir
        for parent in [novel_dir.parent, novel_dir.parent.parent / "拆文库"]:
            candidates = []
            sb_dir = parent / source_book
            if sb_dir.exists():
                candidates.append(sb_dir)
            if parent.name == source_book:
                candidates.append(parent)
            for sd in candidates:
                f = sd / "作品信息" / "套路分析.xml"
                if f.exists():
                    return _simplify_xml(f.read_text(encoding='utf-8'))
    # fallback: 从仿写项目本身读取
    f = self.novel_dir / "作品信息" / "套路分析.xml"
    if f.exists():
        return _simplify_xml(f.read_text(encoding='utf-8'))
    return ""

VariableResolver.COMPUTED_HANDLERS["作品信息/套路分析"] = _source_pattern_analysis

# ── 模板自动注册：扫描 schemas/*.schema.xml + *.ref.xml ──
_schema_dir = Path(__file__).parent / "schemas"
if _schema_dir.exists():
    for _f in sorted(_schema_dir.glob("*.schema.xml")):
        _base = _f.name.rsplit(".", 2)[0].replace("-", "_")  # "events.schema" → "events"; "character-rules.ref" → "character_rules"
        _var = f"template_{_base}"
        if _var not in VariableResolver.COMPUTED_HANDLERS:
            @VariableResolver.register_computed(_var)
            def _loader(self, p=_f):
                try: return p.read_text(encoding='utf-8')
                except: return ""
            _loader.__name__ = f"template_{_base}"
    for _f in sorted(_schema_dir.glob("*.ref.xml")):
        _base = _f.name.rsplit(".", 2)[0].replace("-", "_")  # "writing-rules.ref" → "writing_rules"
        _var = f"template_{_base}"
        if _var not in VariableResolver.COMPUTED_HANDLERS:
            @VariableResolver.register_computed(_var)
            def _loader(self, p=_f):
                try: return p.read_text(encoding='utf-8')
                except: return ""
            _loader.__name__ = f"template_{_base}"


# ── 作品篇幅 ──
def _work_length(self):
    """返回作品篇幅描述。"""
    total = self.resolve("总章数")
    try:
        n = int(total)
        if n >= 100:
            label = "长篇"
        elif n >= 30:
            label = "中篇"
        else:
            label = "短篇"
        return f"{label}（共{n}章）"
    except:
        return "长篇"

VariableResolver.COMPUTED_HANDLERS["作品篇幅"] = _work_length

# ── 本卷章数：start - end + 1 ──
def _volume_chapter_count(self):
    s = int(self._ctx("start", 1))
    e = int(self._ctx("end", 1))
    return str(max(0, e - s + 1))

VariableResolver.COMPUTED_HANDLERS["本卷章数"] = _volume_chapter_count


# ── 仿写章纲：从总纲读取实体映射，替换章纲中的源文名字 ──
