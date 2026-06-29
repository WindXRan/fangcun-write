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
    """找主角：优先 role=protagonist，降级到第一个角色卡。"""
    d = self.novel_dir / "作品信息" / "设定" / "角色"
    if not d.exists(): return fallback
    import xml.etree.ElementTree as ET
    import re as _re
    first = None
    for f in sorted(d.glob("*.xml")):
        try:
            text = f.read_text(encoding="utf-8")
            clean = _re.sub(r'```(?:xml)?\n?', '', text).strip()
            clean = _re.sub(r'^.*?(<[a-zA-Z_])', r'\1', clean, flags=_re.DOTALL)
            root = ET.fromstring(clean)
            if root.tag in ("entry", "character"):
                name = root.get("name", "")
                role = root.get("role", "")
                if role == "protagonist":
                    return name
                if first is None:
                    first = name
        except: pass
    return first or fallback

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
    for ext in ("", ".xml"):
        p = self.novel_dir / "正文" / "正文" / f"第{N}章{ext}"
        if p.exists():
            text = p.read_text(encoding="utf-8")
            clean = re.sub(r'<[^>]+>', '', text).strip()
            return clean
    return "（无本章正文）"

VariableResolver.COMPUTED_HANDLERS["本章正文"] = _current_chapter_text

def _prev_chapter_tail(self, limit=5):
    """前文全文：最近最多 limit 章的完整正文。"""
    N = self._ctx("N", 1)
    if N <= 1: return "（无前文）"
    import re
    parts = []
    start = max(1, N - limit)
    for i in range(start, N):
        for ext in ("", ".xml"):
            p = self.novel_dir / "正文" / "正文" / f"第{i}章{ext}"
            if p.exists():
                text = p.read_text(encoding="utf-8")
                clean = re.sub(r'<[^>]+>', '', text).strip()
                parts.append(f"---第{i}章---\n{clean}")
                break
    return "\n\n".join(parts) if parts else "（无前文）"

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
        # fallback: 列出所有可用角色名
        d = self.novel_dir / "作品信息" / "设定" / "角色"
        if d.exists():
            names = [f.stem for f in sorted(d.glob("*.xml"))]
            return f"可用角色：{'、'.join(names)}" if names else "（无角色卡）"
        return "（无章纲，请先生成章纲）"

    # 提取 <characters> 字段
    m = _re.search(r'<characters>([^<]+)</characters>', guide_text)
    if not m:
        return "（章纲中未标记出场角色）"
    raw = m.group(1).strip()
    # 解析角色名（逗号/顿号/空格分隔）
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
    """从源文项目读取当前章节正文。需要 source_book + 拆文库/ 或同级目录。"""
    N = self._ctx("N", 1)
    source_book = self._user_overrides.get("source_book", "")
    if not source_book:
        return ""

    # 从用户覆盖中取
    manual = self._user_overrides.get("源文对照", "")
    if manual:
        return manual

    # 尝试从 source_book 的目录读取
    # 项目结构: projects/{author}/{仿写书名}/
    # source_book 同级: projects/{author}/{source_book}/
    # 或拆文库/{source_book}/
    novel_dir = self.novel_dir  # 仿写项目目录
    for parent in [novel_dir.parent, novel_dir.parent.parent / "拆文库"]:
        # source_book 可能是独立项目（projects/A/SB/），也可能是同级（projects/SB/）
        candidates = []
        sb_dir = parent / source_book
        if sb_dir.exists():
            candidates.append(sb_dir)
        # 源文就在 parent 本身（projects/{source_book}/）
        if parent.name == source_book:
            candidates.append(parent)
        for sb_dir in candidates:
            for pat in [f"正文/正文/第{N}章*.txt", f"正文/正文/第{N}章*.xml",
                        f"源文/第{N}章*.txt", f"第{N}章*.txt"]:
                files = sorted(sb_dir.glob(pat))
                if files:
                    return files[0].read_text(encoding='utf-8', errors='replace')
    return ""

VariableResolver.COMPUTED_HANDLERS["源文对照"] = _source_chapter



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
