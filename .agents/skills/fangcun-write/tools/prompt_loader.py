"""Prompt 加载器。优先 builtin/*/preset.xml，fallback 旧 .md。"""
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# XSD schema validation (optional — pip install xmlschema)
try:
    import xmlschema
    HAS_XMLSCHEMA = True
except ImportError:
    HAS_XMLSCHEMA = False
    xmlschema = None

_FILE = Path(__file__).resolve()
_TOOLS = _FILE.parent / "builtin"          # tools/builtin/（preset.xml 目录）

# Schema file path — must exist alongside the XML presets
_SCHEMA_PATH = _TOOLS / "preset-schema.xsd"
_SCHEMA_CACHE = None

# prompt_meta（旧 .md 回退用，可能不存在）
try:
    from prompt_meta import parse_frontmatter, safe_format
except ImportError:
    parse_frontmatter = safe_format = None

# VariableResolver（同 package 内，无跨 skill import）
try:
    from variable_resolver import VariableResolver, AT_VAR_PATTERN
except ImportError:
    VariableResolver = None
    AT_VAR_PATTERN = None


# 变量标注解析：变量名(必选) / 变量名(可选)
_VAR_ANNOT_PATTERN = re.compile(r'^([^(]+)(?:\(([^)]*)\))?$')


def _parse_var_annotations(raw: str) -> list[dict]:
    """解析 <variables> 标签内容，返回 [{name, required, label}]。"""
    result = []
    for part in [v.strip() for v in raw.split(",") if v.strip()]:
        m = _VAR_ANNOT_PATTERN.match(part)
        if m:
            name = m.group(1).strip()
            annot = m.group(2)
            if annot in ("必选", "required"):
                result.append({"name": name, "required": True, "label": "必选"})
            elif annot in ("可选", "optional"):
                result.append({"name": name, "required": False, "label": "可选"})
            else:
                result.append({"name": name, "required": True, "label": ""})
    return result


def _validate_xml_schema(preset_name: str, xml_path: Path, strict: bool) -> list[str]:
    """Validate an XML preset file against the XSD schema.

    Compiles the schema once and caches it.  Returns a list of
    human-readable error messages (empty list = valid).

    strict=True  → errors printed at [ERROR] level (caller may raise).
    strict=False → errors printed at [WARN] level only.
    """
    global _SCHEMA_CACHE

    if not HAS_XMLSCHEMA:
        print("  [WARN] xmlschema 未安装，跳过 XSD 校验。pip install xmlschema 启用。")
        return []

    if not _SCHEMA_PATH.exists():
        print(f"  [WARN] schema 文件不存在: {_SCHEMA_PATH}")
        return []

    try:
        if _SCHEMA_CACHE is None:
            _SCHEMA_CACHE = xmlschema.XMLSchema(_SCHEMA_PATH)

        errors: list[str] = []
        for validation_error in _SCHEMA_CACHE.iter_errors(xml_path):
            # Extract the XPath / element path for a clear error location
            elem = validation_error.elem
            if elem is not None:
                element_path = _element_xpath(elem)
            else:
                element_path = getattr(validation_error, 'path', '?')

            msg = (
                f"  [{'ERROR' if strict else 'WARN'}] "
                f"XML 校验失败: {preset_name}.xml\n"
                f"      位置: {element_path}\n"
                f"      原因: {validation_error.message}"
            )
            errors.append(msg)

        return errors

    except xmlschema.XMLSchemaException as ex:
        return [
            f"  [ERROR] schema 加载/解析失败: {_SCHEMA_PATH.name}\n"
            f"      原因: {ex}"
        ]
    except Exception as ex:
        return [
            f"  [ERROR] XSD 校验异常: {ex}"
        ]


def _element_xpath(elem) -> str:
    """Build a minimal XPath-like string for an Element (for error reporting)."""
    parts = []
    cur = elem
    while cur is not None:
        parts.append(cur.tag)
        cur = cur.getparent() if hasattr(cur, 'getparent') else None
        if cur is not None and hasattr(cur, 'tag'):
            # stop at <tool> root to keep output concise
            if cur.tag == 'tool':
                break
    return '/'.join(reversed(parts)) or elem.tag


def _read_preset(name, strict=False):
    """读取 builtin/{name}.xml。

    Parameters
    ----------
    name : str
        Preset name (with or without .md suffix).
    strict : bool
        When True, XSD validation errors raise ValueError.
        When False, errors are printed as warnings and execution continues.
    """
    name = name.replace(".md", "")
    d = _TOOLS / f"{name}.xml"
    if not d.exists():
        return None, [], []
    try:
        t = ET.parse(d)
        r = t.getroot()

        # XSD schema validation — run immediately after parsing
        errors = _validate_xml_schema(name, d, strict=strict)
        if errors:
            for e in errors:
                print(e, file=sys.stderr)
            if strict:
                raise ValueError(
                    f"Preset '{name}.xml' 未通过 XSD schema 校验，"
                    f"共 {len(errors)} 个错误。"
                )

        pe = r.find("prompt")
        prompt_text = pe.text.strip() if pe is not None and pe.text else None

        # 提取 <variables> 声明（工具预设声明的 @变量名列表，支持 必选/可选 标注）
        ve = r.find("variables")
        declared_vars = []
        var_metas = []
        if ve is not None and ve.text:
            var_metas = _parse_var_annotations(ve.text)
            declared_vars = [m["name"] for m in var_metas]

        return prompt_text, declared_vars, var_metas

    except ValueError:
        raise  # re-raise strict-mode ValueError as-is
    except ET.ParseError as ex:
        print(f"  [ERROR] XML 语法错误: {name}.xml — {ex}", file=sys.stderr)
        if strict:
            raise
        return None, [], []
    except Exception:
        return None, [], []


def _validate_preset_variables(
    preset_name: str,
    prompt_text: str,
    declared_vars: list[str],
    var_metas: list[dict],
    resolver,
    replacements: dict | None,
) -> list[str]:
    """校验预设的 @变量 是否有注入值。返回缺失变量列表。"""
    missing: list[str] = []

    # 1. 编译时校验：基于 preset.xml 声明的 <variables>
    if declared_vars:
        available = set()
        if resolver:
            available.update(resolver.defs.keys())
            available.update(resolver._user_overrides.keys())
            available.update(str(k) for k in resolver._runtime_context.keys())
        if replacements:
            available.update(replacements.keys())

        # 按标注分组
        required_vars = {m["name"] for m in var_metas if m.get("required")}
        optional_vars = {m["name"] for m in var_metas if not m.get("required")}

        for v in declared_vars:
            if v not in available:
                if v in required_vars:
                    missing.append(v)
                # optional vars missing is fine — they have defaults

        if missing:
            print(
                f"  [WARN] 预设 '{preset_name}' 缺少必传变量: {missing}"
            )

    # 2. 运行时校验：检查 prompt 中是否有残留的 @[未定义:xxx]
    if AT_VAR_PATTERN and resolver:
        # 找出 prompt 中所有 @变量
        used_vars = set(AT_VAR_PATTERN.findall(prompt_text))
        unresolved = []
        for v in used_vars:
            val = resolver.resolve(v)
            if val.startswith("@[未定义:") or val.startswith("@[未知"):
                unresolved.append(v)
        if unresolved:
            print(
                f"  [WARN] 预设 '{preset_name}' 渲染后仍有 "
                f"{len(unresolved)} 个未定义变量: {unresolved}"
            )
            missing.extend(unresolved)

    return missing


def load_preset(name, strict=False):
    """Public entry point: load a preset by name.

    Thin wrapper around _read_preset that also validates the XSD schema.

    Parameters
    ----------
    name : str
        Preset name (without path/extension).
    strict : bool
        When True, XSD validation failure raises ValueError.
    """
    return _read_preset(name, strict=strict)


def load_prompt(prompt_path, base_dir, replacements=None, mode=None,
                project_dir=None, source_dir=None, strict=False):
    prompt_file = Path(prompt_path)
    if not prompt_file.is_absolute():
        prompt_file = Path(base_dir) / prompt_path

    raw, declared_vars, var_metas = _read_preset(prompt_file.stem, strict=strict)

    if raw is None:
        if prompt_file.exists():
            raw = prompt_file.read_text(encoding="utf-8")
            meta, raw = parse_frontmatter(raw)
        else:
            raise FileNotFoundError(f"Prompt 不存在: {prompt_file}")

    if VariableResolver and project_dir:
        try:
            r = VariableResolver(str(project_dir))
            if source_dir:
                r.set_source_dir(source_dir)
            ctx = {}
            if replacements:
                for k in ("N", "start", "end", "total_chapters", "source_book", "target_words"):
                    if k in replacements:
                        try:
                            ctx[k] = int(replacements[k])
                        except (ValueError, TypeError):
                            ctx[k] = replacements[k]
                if ctx:
                    r.set_context(preset=prompt_file.stem, **ctx)
                else:
                    r.set_context(preset=prompt_file.stem)
                overs = {
                    k: str(v)
                    for k, v in replacements.items()
                    if isinstance(v, str) and v and k not in ctx
                }
                if overs:
                    r.set_user_overrides(overs)

            # 变量契约校验：预设声明 vs 实际注入
            _validate_preset_variables(
                prompt_file.stem, raw, declared_vars, var_metas, r, replacements
            )

            result = r.render(raw)

            # 渲染后运行时校验：防止漏网之鱼
            if AT_VAR_PATTERN:
                leftovers = AT_VAR_PATTERN.findall(result)
                # 只报未定义的（resolve() 会保留 unknown 为 @[未定义:xxx]）
                unresolved = [
                    v
                    for v in leftovers
                    if r.resolve(v).startswith("@[未定义:")
                ]
                if unresolved:
                    print(f"  [WARN] {len(unresolved)} 个 @变量未解析（保留原文）: {unresolved[:5]}")

            return result
        except Exception as ex:
            print(f"  [WARN] VariableResolver 失败: {ex}，回退 safe_format")
            # fallthrough to safe_format

    if replacements:
        return safe_format(raw, replacements)
    return raw


def make_book_data_replacements(book_data):
    if not book_data:
        return {}
    result = {}
    for ch in book_data.get("characters", []) or []:
        if isinstance(ch, dict):
            n, r = ch.get("name", ""), (ch.get("role") or "").lower()
            if "男主" in r or "protagonist" in r:
                result.setdefault("男主名", n)
            elif "女主" in r:
                result.setdefault("女主名", n)
    t = book_data.get("title") or book_data.get("书名", "")
    if t:
        result["故事名称"] = result["新书名"] = t
    return result
