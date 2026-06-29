"""文件操作工具：项目初始化、输出文件保存、XML属性注入。"""
import os, re
from pathlib import Path

def init_project(project_dir: str, story_name: str = "", channel: str = "男频"):
    """创建新项目目录结构。"""
    p = Path(project_dir)
    p.mkdir(parents=True, exist_ok=True)
    for d in ["正文/卷纲", "正文/章纲", "正文/正文",
              "作品信息/设定/角色", "作品信息/设定/背景",
              "作品信息/设定/势力", "作品信息/设定/地点",
              "作品信息/设定/物品", "作品信息/主题"]:
        (p / d).mkdir(parents=True, exist_ok=True)
    # 确保 project.xml 存在（含故事名和频道）
    proj_xml = p / "作品信息" / "project.xml"
    if not proj_xml.exists():
        name = story_name or Path(project_dir).name
        proj_xml.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<project><story_name>{name}</story_name>'
            f'<channel>{channel}</channel></project>\n',
            encoding='utf-8')


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
                # Fix: 剥离 markdown 代码块包裹（LLM 经常输出 ```xml ... ```）
                content = re.sub(r'^```\w*\s*\n?', '', content)
                content = re.sub(r'\n?```\s*$', '', content)
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(content, encoding='utf-8')
                saved.append(path)
        if saved:
            return saved

    # 2. 降级：旧 ==== path ==== 格式
    for m in re.finditer(r'====\s*([^\n=]+)\s*====\s*\n(.*?)(?=\n====|\Z)', text, re.DOTALL):
        path = m.group(1).strip()
        content = m.group(2).strip()
        content = re.sub(r'^```\w*\s*\n?', '', content)
        content = re.sub(r'\n?```\s*$', '', content)
        if not path or not content:
            continue
        fp = Path(project_dir) / path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding='utf-8')
        saved.append(path)
    return saved


# ─── 工具执行 ─────────────────────────────────────────────
_SINGLE_FILE_MAP = {
    "synopsis-generate": "作品信息/主题/简介.xml",
    "outline-generate": "作品信息/主题/总纲.xml",
    "tags-generate": "作品信息/主题/标签.xml",
}


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


