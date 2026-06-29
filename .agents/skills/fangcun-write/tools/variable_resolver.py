"""VariableResolver：统一 @变量 解析引擎。

替代现有三套语法（{变量}、@path、【标签】），全部统一为 @变量名。
按 variable_definitions.json 定义的六类变量，自动提取 + 手动覆盖。
"""
import json
import re
import traceback
from pathlib import Path
from typing import Any, Optional


# ─── @ 变量正则 ────────────────────────────────────────────────
AT_VAR_PATTERN = re.compile(r"@([一-鿿　-〿＀-￯a-zA-Z0-9_/{}.]+)")


class VariableResolver:
    """解析 prompt 中的 @变量名，从变量池取值替换。"""

    def __init__(self, novel_dir: str, definitions_path: str = None):
        self.novel_dir = Path(novel_dir)
        self.defs = self._load_definitions(definitions_path)
        self._cache: dict[str, str] = {}  # 提取结果缓存
        self._user_overrides: dict[str, str] = {}  # 用户手动覆盖值
        self._runtime_context: dict[str, Any] = {}  # 运行时上下文（N 等）

    # ─── 加载定义 ────────────────────────────────────────────

    def _load_definitions(self, path: str = None) -> dict:
        if path is None:
            path = Path(__file__).parent / "variable_definitions.xml"
        return self._parse_definitions_xml(path)

    def _parse_definitions_xml(self, path: str) -> dict:
        """解析 variable_definitions.xml，返回 {变量名: {type, category, ...}}"""
        import xml.etree.ElementTree as ET
        tree = ET.parse(path)
        root = tree.getroot()
        defs = {}
        for var_el in root.find("variables").findall("variable"):
            name = var_el.get("name")
            vdef = {
                "category": var_el.get("category", ""),
                "type": var_el.get("type", "text"),
                "source": var_el.get("source", "auto_extract"),
                "handler": var_el.get("handler", ""),  # computed 变量的注册名
                "description": "",
            }
            for child in var_el:
                tag = child.tag
                if tag == "description":
                    vdef["description"] = (child.text or "").strip()
                elif tag == "extract":
                    vdef["extract"] = {k: v for k, v in child.attrib.items()}
                elif tag == "fallback":
                    vdef["fallback"] = (child.text or "").strip()
                elif tag == "compute":
                    vdef["compute"] = (child.text or "").strip()
                elif tag == "options":
                    vdef["options"] = [o.strip() for o in (child.text or "").split(",")]
                elif tag == "default":
                    vdef["default"] = (child.text or "").strip()
            defs[name] = vdef
        return defs

    # ─── 运行时上下文 ──────────────────────────────────────────

    def set_context(self, **kwargs):
        """设置运行时上下文（如 N=45, start=1, end=192 等）。"""
        self._runtime_context.update(kwargs)
        self._cache.clear()  # 上下文变了，缓存失效

    def set_user_overrides(self, overrides: dict[str, str]):
        self._user_overrides.update(overrides)
        self._cache.clear()

    def set_source_dir(self, source_dir: str):
        """设置源文目录，用于 _resolve_source_path 查找。"""
        self._runtime_context["source_dir"] = source_dir
        self._cache.clear()

    def _ctx(self, key: str, default=None):
        return self._runtime_context.get(key, default)

    # ─── 核心：解析 @变量 → 值 ─────────────────────────────────

    def resolve(self, var_name: str) -> str:
        """解析单个变量。优先级：用户覆盖 > 缓存 > 自动提取。"""
        if var_name in self._user_overrides:
            return self._user_overrides[var_name]
        if var_name in self._cache:
            return self._cache[var_name]

        var_def = self.defs.get(var_name)
        if not var_def:
            # 1. computed handler 直查（无需 XML 定义）
            if var_name in self.COMPUTED_HANDLERS:
                val = self.COMPUTED_HANDLERS[var_name](self)
                self._cache[var_name] = val
                return val
            # 2. 含 / 的 → 尝试作为项目相对路径解析
            nd = self.novel_dir
            if "/" in var_name and nd:
                # 替换 {N} 为当前章节号
                path = var_name.replace("{N}", str(self._ctx("N", ""))).replace("$N", str(self._ctx("N", "")))
                for ext in ("", ".xml", ".md", ".json"):
                    p = nd / f"{path}{ext}"
                    if not p.exists():
                        continue
                    if p.is_dir():
                        # 目录：拼接所有 .xml 文件
                        parts = []
                        try:
                            for f in sorted(p.glob("*.xml")):
                                parts.append(f.read_text(encoding='utf-8'))
                        except Exception:
                            pass
                        if parts:
                            val = "\n\n".join(parts)
                            self._cache[var_name] = val
                            return val
                    else:
                        # Fix 3: 跳过 schema 文件（它们是输出模板，不是数据）
                        if p.name.endswith('.schema.xml'):
                            continue
                        val = p.read_text(encoding='utf-8')
                        if p.suffix == '.xml':
                            val = _simplify_xml(val)
                        self._cache[var_name] = val
                        return val
            return f"@[未定义:{var_name}]"

        value = self._resolve_by_type(var_name, var_def)
        self._cache[var_name] = value
        return value

    def _resolve_by_type(self, name: str, var_def: dict) -> str:
        vtype = var_def.get("type", "text")
        source = var_def.get("source", "auto_extract")

        if source == "user_input":
            return ""  # 用户未填则空

        if vtype == "text":
            return self._resolve_text(name, var_def)
        elif vtype == "file_ref":
            return self._resolve_file_ref(name, var_def)
        elif vtype == "computed":
            return self._resolve_computed(name, var_def)
        elif vtype == "option":
            return var_def.get("default", "")
        elif vtype == "range":
            s = self._ctx("start", 1)
            e = self._ctx("end", 1)
            return f"第{s}-{e}章"
        return f"@[未知类型:{vtype}]"

    def _resolve_text(self, name: str, var_def: dict) -> str:
        extract = var_def.get("extract", {})
        if not extract:
            return var_def.get("fallback", "")

        # config 来源：从 user_overrides 取值（不读文件）
        if extract.get("from") == "config":
            field = extract.get("field", name)
            return self._user_overrides.get(field, "") or var_def.get("fallback", "")

        value = self._extract_value(extract)
        if value:
            return value

        # fallback：若是文件路径，尝试读取
        fb = var_def.get("fallback", "")
        if "/" in fb or fb.endswith(".md") or fb.endswith(".json") or fb.endswith(".xml"):
            fb_path = self._resolve_source_path(fb)
            if fb_path and fb_path.exists():
                return fb_path.read_text(encoding="utf-8")
        return fb

    def _resolve_file_ref(self, name: str, var_def: dict) -> str:
        extract = var_def.get("extract", {})
        compute = var_def.get("compute", "")
        if compute:
            path = self._fmt_path(compute)
            return self._read_file(self.novel_dir / path)
        if extract:
            val = self._extract_value(extract)
            if val:
                return val
            fb = var_def.get("fallback", "")
            if fb is not None:
                return fb
            return f"@[未找到:{name}]"
        return f"@[未配置来源:{name}]"

    # ─── computed 变量注册表 ───────────────────────────────────
    # handler 名 → 回调函数。通过 variable_definitions.xml 的 handler 属性关联。
    COMPUTED_HANDLERS: dict[str, callable] = {}

    @classmethod
    def register_computed(cls, handler_name: str):
        """装饰器：注册 computed handler。"""
        def wrapper(fn):
            cls.COMPUTED_HANDLERS[handler_name] = fn
            return fn
        return wrapper

    def _resolve_computed(self, name: str, var_def: dict) -> str:
        handler_name = var_def.get("handler", "")
        compute = var_def.get("compute", "")

        # 1. handler 名优先（方向二：解耦 XML 表达式与 Python 实现）
        if handler_name and handler_name in self.COMPUTED_HANDLERS:
            return self.COMPUTED_HANDLERS[handler_name](self)

        # 2. 旧兼容：compute 表达式精确匹配
        if not compute:
            return f"@[无compute规则:{name}]"

        _legacy_handlers = {
            "total_chapters * avg_words_per_chapter": self._compute_total_words,
            "N from pipeline context": lambda: str(self._ctx("N", "?")),
            "source_word_count * 1.0 ±10%": self._compute_target_words,
            "target_words * 0.9": self._compute_target_words_min,
            "target_words * 1.1": self._compute_target_words_max,
            "count_chars(source_ch_N)": self._compute_source_chars,
            "avg_sentence_length(source_ch_N)": self._compute_source_sent_len,
            "summarize_last_3_chapters(N)": self._compute_recent_summary,
            "style_anchors for chapter N": self._compute_style_anchors,
        }
        if compute in _legacy_handlers:
            return _legacy_handlers[compute]()

        # 3. "last N chars" 后缀
        if "last 1500 chars" in compute:
            path_part = compute.split(" last 1500 chars")[0].strip()
            path = self._fmt_path(path_part)
            text = self._read_file(self.novel_dir / path)
            return text[-1500:] if len(text) > 1500 else text

        # 4. "full content" 后缀
        if "full content" in compute:
            path_part = compute.split(" full content")[0].strip()
            path = self._fmt_path(path_part)
            return self._read_file(self.novel_dir / path)

        # 5. 纯动态路径
        if compute.startswith("guides/") or compute.startswith("chapters/"):
            path = self._fmt_path(compute)
            return self._read_file(self.novel_dir / path)

        # 6. _cache/ → 拆文库
        if compute.startswith("_cache/"):
            path = self._fmt_path(compute)
            resolved = self._resolve_source_path(path)
            return self._read_file(resolved) if resolved else ""

        return f"@[未知compute:{name}]"

    def _fmt_path(self, pattern: str) -> str:
        """将路径中的 {N} / {N-1:03d} / {start} 等格式化。"""
        ctx = dict(self._runtime_context)
        N = int(ctx.get("N", 1))
        # 基础变量
        ctx["N"] = str(N)
        ctx["N03d"] = f"{N:03d}"
        ctx["N_minus_1"] = f"{N - 1:03d}" if N > 1 else "001"
        ctx["N_plus_1"] = f"{N + 1:03d}"
        ctx["start"] = str(ctx.get("start", "?"))
        ctx["end"] = str(ctx.get("end", "?"))
        # {N-1:03d} → {N_minus_1}
        pattern = pattern.replace("{N-1:03d}", "{N_minus_1}")
        pattern = pattern.replace("{N-1}", "{N_minus_1}")
        pattern = pattern.replace("{N:03d}", "{N03d}")
        return pattern.format(**ctx)

    # ─── 提取方法 ────────────────────────────────────────────

    def _extract_value(self, extract: dict) -> Optional[str]:
        method = extract.get("method", "read")
        path = self._resolve_source_path(extract.get("from", ""))

        if not path or not path.exists():
            return None

        if method == "read_dir":
            if path.is_dir():
                parts = []
                for f in sorted(path.glob("*.xml")):
                    try: parts.append(f.read_text(encoding="utf-8"))
                    except Exception: pass
                return "\n".join(parts)
            return ""

        content = path.read_text(encoding="utf-8")

        if method == "xpath":
            import xml.etree.ElementTree as ET
            xp = extract.get("xpath", "")
            try:
                root = ET.fromstring(content)
                # 搜索目标：先查 root 自己，再查 children
                target_tag = xp.replace(".//", "").split("/@")[0].split("/")[0]
                if root.tag == target_tag:
                    elem = root
                else:
                    elem = root.find(xp)
                if "/@" in xp:
                    _, attr = xp.rsplit("/@", 1)
                    return elem.get(attr, "") if elem is not None else None
                else:
                    return (elem.text or "").strip() if elem is not None else None
            except Exception:
                traceback.print_exc()
                return None
        if method == "read":
            return content
        if method == "regex":
            pattern = extract.get("pattern", "")
            m = re.search(pattern, content, re.MULTILINE)
            return m.group(1).strip() if m else None
        if method == "section":
            section = extract.get("section", "")
            return self._extract_section(content, section)
        if method == "tag":
            tag = extract.get("tag", "")
            m = re.search(rf"<{tag}>(.*?)</{tag}>", content, re.DOTALL)
            return m.group(1).strip() if m else None
        if method == "xml_name_map":
            return self._extract_name_map(content)
        if method == "parse":
            return content  # events.xml / volumes.xml 全文返回
        return content

    def _resolve_source_path(self, source: str) -> Optional[Path]:
        """解析提取来源路径。

        优先级：
        1. novel_dir / source（项目内文件，如 meta/concept.md）
        2. novel_dir / "meta" / source（meta 子目录）
        3. 拆文库/{source_book}/source（源文分析，source 前缀 _cache/ 时）
        4. 拆文库/*/source（兜底遍历）
        """
        if not source:
            return None

        # 1. 项目内直接查找
        p = self.novel_dir / source
        if p.exists():
            return p

        # 2. meta/ 子目录（concept.md, characters.md 等）
        p = self.novel_dir / "meta" / source
        if p.exists():
            return p

        # 3. 源文分析 → 拆文库
        source_book = self._ctx("source_book", "") or self._user_overrides.get("source_book", "")
        analyse_root = self.novel_dir.parent.parent / "拆文库"

        if source.startswith("_cache/"):
            source = source[len("_cache/"):]

        # 有 source_book 时精确定位
        if source_book and analyse_root.exists():
            p = analyse_root / source_book / source
            if p.exists():
                return p

        # 兜底遍历
        if analyse_root.exists():
            for d in sorted(analyse_root.iterdir(), reverse=True):
                p = d / source
                if p.exists():
                    return p

        return None

    def _read_file(self, path: Path) -> str:
        """安全读文件，不存在返回空。"""
        try:
            if path.exists():
                return path.read_text(encoding="utf-8")
            return ""
        except Exception:
            return ""

    @staticmethod
    def _extract_section(content: str, section_name: str) -> str:
        """提取 Markdown ## section 的内容。"""
        pattern = rf"##\s+{re.escape(section_name)}\s*\n(.*?)(?=\n##\s|\Z)"
        m = re.search(pattern, content, re.DOTALL)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _extract_name_map(content: str) -> str:
        """从 characters.md 提取 XML name_map。"""
        m = re.search(r"<name_map>(.*?)</name_map>", content, re.DOTALL)
        return m.group(1).strip() if m else content

    # ─── compute 处理器 ──────────────────────────────────────

    def _compute_total_words(self) -> str:
        """从 project_dir 统计全部已完成章的均字数 × 总章数。"""
        chapters_dir = self.novel_dir / "chapters"
        if not chapters_dir.exists():
            return "未知"
        files = sorted(chapters_dir.glob("ch_*.txt"))
        if not files:
            return "未知"
        total = 0
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
                total += len(text.replace("\n", "").replace(" ", ""))
            except Exception:
                pass
        avg = total // len(files) if files else 0
        total_chs = self._ctx("total_chapters", len(files))
        return f"{avg * total_chs:,}"

    def _compute_target_words(self) -> str:
        """目标字数 = 源文章字数 × 1.0。"""
        source_chars = self._source_chars()
        return str(source_chars) if source_chars else self._ctx("target_words", "2000")

    def _compute_target_words_min(self) -> str:
        source = self._source_chars()
        target = source or int(self._ctx("target_words", "2000"))
        return str(int(int(target) * 0.9))

    def _compute_target_words_max(self) -> str:
        source = self._source_chars()
        target = source or int(self._ctx("target_words", "2000"))
        return str(int(int(target) * 1.1))

    def _compute_source_chars(self) -> str:
        return str(self._source_chars())

    def _compute_source_sent_len(self) -> str:
        # 从 拆文库/styles/ 读取源文句长
        N = self._ctx("N", 1)
        resolved = self._resolve_source_path(f"styles/style_{N:03d}.md")
        text = self._read_file(resolved) if resolved else ""
        if text:
            m = re.search(r"句长[：:]\s*([\d.]+)", text)
            if m:
                return m.group(1)
        return "?"

    def _compute_recent_summary(self) -> str:
        N = self._ctx("N", 1)
        summaries = []
        for i in range(max(1, N - 3), N):
            text = ""
            for ext in (".xml", ".txt"):
                p = self.novel_dir / "正文" / "正文" / f"第{i}章{ext}"
                if p.exists():
                    text = p.read_text(encoding="utf-8")
                    break
            if text:
                # 取每章第一段作为摘要
                first_line = text.strip().split("\n")[0] if text else ""
                summaries.append(f"第{i}章: {first_line[:80]}...")
        return "\n".join(summaries)

    def _compute_previous_n_chapters(self, n=20) -> str:
        """读取前 N 章完整正文，不截取。"""
        N = self._ctx("N", 1)
        parts = []
        from utils import load_chapter_text
        for i in range(max(1, N - n), N):
            try:
                text = load_chapter_text(str(self.novel_dir), i)
                if text:
                    parts.append(f"--- 第{i}章 ---\n{text.strip()}")
            except Exception:
                continue
        return "\n\n".join(parts) if parts else "（无前文）"

    def _compute_style_anchors(self) -> str:
        N = self._ctx("N", 1)
        resolved = self._resolve_source_path(f"styles/style_{N:03d}.md")
        return self._read_file(resolved) if resolved else ""

    def _source_chars(self) -> int:
        """获取源文当前章的字数。"""
        N = self._ctx("N", 1)
        # 从源文目录读
        source_dir = self._ctx("source_dir", "")
        if source_dir:
            for pat in [f"第{N}章*.txt", f"ch_{N:03d}.txt", f"第{N}章*.md"]:
                files = list(Path(source_dir).glob(pat))
                if files:
                    text = files[0].read_text(encoding="utf-8")
                    return len(text.replace("\n", "").replace(" ", ""))
        return 0

    # ─── 渲染 prompt ────────────────────────────────────────

    # ─── @引用 类别注册 ─────────────────────────────────────
    #  @类别:名称 → 自动查找项目文件并注入内容
    REF_CATEGORIES = {
        "角色": "作品信息/设定/角色",
        "设定": "作品信息/设定",
        "章节": "正文/正文",
        "纲要": "正文/章纲",
        "卷纲": "正文/卷纲",
    }

    def _resolve_ref(self, category: str, name: str) -> str:
        """解析 @类别:名称 引用。"""
        base = self.REF_CATEGORIES.get(category)
        if base:
            d = self.novel_dir / base
            if not d.exists():
                return f"（无{category}目录）"
            for ext in ("", ".xml", ".md", ".txt"):
                for f in sorted(d.glob(f"{name}{ext}")):
                    return f.read_text(encoding="utf-8")
            candidates = [f.stem for f in sorted(d.glob("*")) if f.is_file()]
            return f"（未找到{category}「{name}」，可用：{'、'.join(candidates[:5])}）"

        simple_map = {
            "标签": ("作品信息/主题/标签.xml", 2000),
            "总纲": ("作品信息/主题/总纲.xml", 50000),
            "简介": ("作品信息/主题/简介.xml", 2000),
        }
        entry = simple_map.get(category)
        if entry:
            target, limit = entry
            p = self.novel_dir / target
            if p.exists():
                import re
                raw = p.read_text(encoding="utf-8")
                # name 非空 → 按结构化字段路径提取子元素
                if name:
                    import xml.etree.ElementTree as ET
                    try:
                        tree = ET.parse(str(p))
                        root = tree.getroot()
                        parts = name.split(".")
                        elem = root
                        for part in parts:
                            attr_match = re.match(r'(\w+)@(\w+)=(.+)', part)
                            if attr_match:
                                tag, attr_key, attr_val = attr_match.groups()
                                found = None
                                for child in elem.findall(tag):
                                    if child.get(attr_key) == attr_val:
                                        found = child
                                        break
                                if found is not None:
                                    elem = found
                                else:
                                    return f"（未找到{category}/{name}）"
                            else:
                                found = elem.find(part)
                                if found is not None:
                                    elem = found
                                else:
                                    return f"（未找到{category}/{name}）"
                        text = re.sub(r'<[^>]+>', '', ET.tostring(elem, encoding='unicode'))
                        return text.strip()
                    except Exception:
                        pass  # fallback to full content
                text = re.sub(r'<[^>]+>', '', raw)
                return text.strip()
            return f"（{category}不存在，请先生成）"
        return f"（未知引用类别：{category}）"

    def render(self, template: str) -> str:
        """将模板中的 @变量名 全部替换为值。支持条件块 {#var}...{/var} 和 XPath 提取 @变量:元素名。"""
        # Fix 5: 解析 XPath 提取语法 @变量:元素名 → @变量，标记提取目标
        _extract_target = None
        _xm = re.match(r'^@([^:]+):([a-zA-Z_]+)', template)
        if _xm:
            template = '@' + _xm.group(1)
            _extract_target = _xm.group(2)

        known = set(self.defs.keys()) | set(self._user_overrides.keys())
        known.update(k for k in self.COMPUTED_HANDLERS if k not in known)
        known = sorted(known, key=len, reverse=True)

        # 第一遍：替换 @变量
        result = []
        i = 0
        while i < len(template):
            if template[i] == '@':
                matched = False
                for name in known:
                    if template.startswith('@' + name, i):
                        val = self.resolve(name)
                        # Fix 5: 如果指定了提取目标，从 XML 中提取指定元素
                        if _extract_target and val:
                            try:
                                import xml.etree.ElementTree as ET
                                _root = ET.fromstring(f'<root>{val}</root>')
                                _found = _root.find(f'.//{_extract_target}')
                                if _found is not None:
                                    val = _found.text or ''
                            except Exception:
                                pass
                        result.append(val)
                        i += len(name) + 1
                        matched = True
                        break
                if not matched:
                    # 2a. 尝试 @类别:名称 引用（带冒号）
                    m = re.match(r'@([一-鿿a-zA-Z]+)[：:](.+?)(?=[，。；\s\n）\)]|$)', template[i:])
                    if m:
                        cat, name = m.group(1), m.group(2).strip()
                        result.append(self._resolve_ref(cat, name))
                        i += m.end()
                        matched = True
                if not matched:
                    # 2b. 无参数引用：@总纲、@标签、@简介
                    m = re.match(r'@(总纲|标签|简介)', template[i:])
                    if m:
                        cat = m.group(1)
                        result.append(self._resolve_ref(cat, ""))
                        i += m.end()
                        matched = True
                if not matched:
                    m = AT_VAR_PATTERN.match(template, i)
                    if m:
                        name = m.group(1)
                        val = self.resolve(name)
                        if not val.startswith('@'):
                            result.append(val)
                            i += len(name) + 1
                            matched = True
                        elif val.startswith('@[未定义:'):
                            result.append(f'@[解析失败:{name}]')
                            i += len(name) + 1
                            matched = True
                    if not matched:
                        result.append(template[i])
                        i += 1
            else:
                result.append(template[i])
                i += 1
        rendered = ''.join(result)

        # Fix 2: 处理条件块 {#var}...{/var}。如果 var 为空（含空字符串），整块删除
        def _process_conditional(text):
            _pat = re.compile(r'\{#([^}]+)\}(.*?)\{/\1\}', re.DOTALL)
            while _pat.search(text):
                text = _pat.sub(lambda m: m.group(2) if self.resolve(m.group(1)) else '', text)
            return text
        rendered = _process_conditional(rendered)

        return rendered

    # ─── 批量提取 ────────────────────────────────────────────

    def extract_all(self, context: dict = None) -> dict[str, dict]:
        """提取全部变量当前值。返回 {key: {value, type, category, source}}。"""
        if context:
            self.set_context(**context)

        result = {}
        for name, var_def in self.defs.items():
            value = self.resolve(name)
            result[name] = {
                "value": value,
                "type": var_def.get("type", "text"),
                "category": var_def.get("category", ""),
                "source": var_def.get("source", ""),
                "description": var_def.get("description", ""),
                "user_override": name in self._user_overrides,
            }
        return result

    def get_variable_schema(self) -> dict:
        """返回变量定义的 schema（给前端渲染面板用）。"""
        categories: dict[str, list] = {}
        for name, var_def in self.defs.items():
            cat = var_def.get("category", "其他")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "key": name,
                "type": var_def.get("type", "text"),
                "source": var_def.get("source", ""),
                "description": var_def.get("description", ""),
                "options": var_def.get("options"),
                "default": var_def.get("default"),
                "current_value": self._cache.get(name, ""),
                "user_override": name in self._user_overrides,
            })
        return categories


# ─── computed handler 注册 — 解耦 XML 表达式与 Python 实现 ──────
# handler 名对应 variable_definitions.xml 中 <variable handler="...">
# 新增 computed 变量只需：1) XML 加 handler 属性 2) 此处注册回调

# 加载外部处理器（handlers.py 在导入时自动注册 COMPUTED_HANDLERS）

def _novel_setting(self):
    """@设定：聚合全部设定数据"""
    import re, xml.etree.ElementTree as ET
    base = self.novel_dir / "作品信息" / "设定"
    parts = []
    for dn in ["角色", "地点", "物品", "势力", "背景"]:
        d = base / dn
        if d.exists():
            for f in sorted(d.glob("*.xml")):
                text = f.read_text(encoding="utf-8", errors="replace")
                if dn == "角色":
                    role = re.search(r'role="([^"]*)"', text)
                    bg = re.search(r'<background>(.*?)</background>', text, re.DOTALL)
                    bgt = bg.group(1).strip()[:80] if bg else ""
                    parts.append("[角色] " + f.stem + " (" + (role.group(1) if role else "?") + "): " + bgt)
                else:
                    desc = re.search(r'<description>(.*?)</description>', text, re.DOTALL)
                    if desc:
                        parts.append("[" + dn + "] " + f.stem + ": " + desc.group(1).strip()[:80])
    relf = base / "关系图谱.xml"
    if relf.exists():
        try:
            tree = ET.parse(relf)
            for r in tree.findall(".//relation"):
                parts.append("[关系] " + r.get("source","") + " -> " + r.get("target","") + " (" + r.get("type","") + "): " + (r.get("description") or "")[:80])
        except: pass
    return "\n".join(parts) if parts else "（无设定数据）"

VariableResolver.COMPUTED_HANDLERS["novel_setting"] = _novel_setting

import handlers
