"""
统一 XML I/O 层。events.xml / volumes.xml 的解析与序列化。
字段定义在此硬编码——schemas/ 的模板只作文档和 AI 参考，不驱动代码。
"""

import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path

EVENTS_FIELDS = [
    "核心事件", "开头承接", "结尾状态", "衔接", "情绪弧线",
    "涉及角色", "主线推进", "支线状态", "信息释放", "人物状态变化", "跨章因果",
]
EXTRA_EVENT_FIELDS = ["所属弧线", "弧内位置"]


# ─── events.xml ─────────────────────────────────────────────────────────

def parse_events(text: str) -> list[dict]:
    """解析 events，容错处理。支持 XML / markdown 包裹 / JSON。"""
    # 1. 剥离 markdown 代码块
    text = re.sub(r'```(?:xml|json)?\s*\n?', '', text)
    text = re.sub(r'```\s*', '', text)

    # 2. 尝试 XML
    events = _parse_events_xml(text)
    if events:
        return events

    # 3. 尝试 JSON
    return _parse_events_json(text)


def _parse_events_xml(text: str) -> list[dict]:
    """XML 解析 events。"""
    try:
        root = ET.fromstring(f"<root>{text}</root>")
        events = []
        for el in root.findall(".//event"):
            event = {}
            # 属性
            for attr_name in ("id", "volume", "arc", "弧"):
                val = el.get(attr_name, "")
                if val:
                    event[attr_name] = val
            if "id" not in event:
                continue
            # 核心字段
            for field in EVENTS_FIELDS + EXTRA_EVENT_FIELDS:
                child = el.find(field)
                if child is not None and child.text:
                    event[field] = _unescape(child.text.strip())
            events.append(event)
        return events
    except ET.ParseError:
        return []


def _parse_events_json(text: str) -> list[dict]:
    """尝试从文本中提取 JSON 数组。"""
    try:
        m = re.search(r'\[.*\]', text, re.DOTALL)
        if m:
            data = json.loads(m.group())
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return []


def save_events(events: list[dict], path: Path):
    """保存 events.xml。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["<events>"]
    for e in events:
        eid = e.get("id", "")
        vol = e.get("volume", "")
        arc = e.get("arc", "")
        attrs = f' id="{eid}"'
        if vol:
            attrs += f' volume="{vol}"'
        if arc:
            attrs += f' arc="{arc}"'
        lines.append(f"  <event{attrs}>")
        for field in EVENTS_FIELDS:
            val = e.get(field)
            if val:
                lines.append(f"    <{field}>{_escape(str(val))}</{field}>")
        lines.append("  </event>")
    lines.append("</events>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_events(path: Path) -> list[dict]:
    """读文件。优先 XML，fallback JSON。"""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".xml":
        return parse_events(text)
    import json
    return json.loads(text)


# ─── volumes.xml ────────────────────────────────────────────────────────

def save_volumes(volumes: list[dict], path: Path):
    """保存 volumes.xml。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["<volumes>"]
    for v in volumes:
        vid = v.get("id", "")
        name = v.get("name", f"第{vid}卷")
        chs = v.get("chapters", [])
        desc = v.get("description", "")
        status = v.get("status", "planned")
        lines.append(f'  <volume id="{vid}" name="{_escape(name)}">')
        if desc:
            lines.append(f"    <description>{_escape(desc)}</description>")
        lines.append(f"    <chapters>{','.join(str(c) for c in chs)}</chapters>")
        lines.append(f"    <status>{_escape(status)}</status>")
        lines.append(f"  </volume>")
    lines.append("</volumes>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_volumes(path: Path) -> list[dict]:
    """读取 volumes.xml → list[dict]。"""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    volumes = []
    for m in re.finditer(r'<volume\s+(.*?)>(.*?)</volume>', text, re.DOTALL):
        attrs, body = m.group(1), m.group(2)
        id_m = re.search(r'id="(\d+)"', attrs)
        if not id_m:
            continue
        name_m = re.search(r'name="([^"]*)"', attrs)
        vol = {"id": id_m.group(1)}
        if name_m:
            vol["name"] = _unescape(name_m.group(1))
        ch_m = re.search(r'<chapters>(.*?)</chapters>', body)
        if ch_m:
            vol["chapters"] = [int(x.strip()) for x in ch_m.group(1).split(",") if x.strip()]
        desc_m = re.search(r'<description>(.*?)</description>', body)
        if desc_m:
            vol["description"] = _unescape(desc_m.group(1).strip())
        status_m = re.search(r'<status>(.*?)</status>', body)
        if status_m:
            vol["status"] = status_m.group(1).strip()
        volumes.append(vol)
    return volumes


# ─── Prompt 注入工具 ──────────────────────────────────────────────────────

def format_events_fields() -> str:
    """将 EVENTS_FIELDS 格式化为 prompt 可注入的清单。"""
    n = len(EVENTS_FIELDS)
    items = [f"{i+1}. &lt;{f}&gt;" for i, f in enumerate(EVENTS_FIELDS)]
    return f"必填字段（{n} 项，与 XML 结构一致）：\n" + "\n".join(items)


# ─── 工具 ───────────────────────────────────────────────────────────────

def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _unescape(text: str) -> str:
    return text.replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
