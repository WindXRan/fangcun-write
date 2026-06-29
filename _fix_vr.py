import sys
filepath = r'c:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\fangcun-write\tools\variable_resolver.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = """# ─── computed handler 注册 — 解耦 XML 表达式与 Python 实现 ──────
# handler 名对应 variable_definitions.xml 中 <variable handler="...">
# 新增 computed 变量只需：1) XML 加 handler 属性 2) 此处注册回调

# 加载外部处理器（handlers.py 在导入时自动注册 COMPUTED_HANDLERS）
import handlers"""

new = """# ─── computed handler 注册 — 解耦 XML 表达式与 Python 实现 ──────
# handler 名对应 variable_definitions.xml 中 <variable handler="...">
# 新增 computed 变量只需：1) XML 加 handler 属性 2) 此处注册回调

def _novel_setting(self):
    '''@设定：聚合全部设定数据'''
    import re, xml.etree.ElementTree as ET
    base = self.novel_dir / "作品信息" / "设定"
    parts = []
    role_dir = base / "角色"
    if role_dir.exists():
        for f in sorted(role_dir.glob("*.xml")):
            text = f.read_text(encoding="utf-8", errors="replace")
            role = re.search(r'role="([^"]*)"', text)
            bg = re.search(r'<background>(.*?)</background>', text, re.DOTALL)
            bg_t = bg.group(1).strip()[:80] if bg else ""
            parts.append("[角色] " + f.stem + " (" + (role.group(1) if role else "?") + "): " + bg_t)
    rel_file = base / "关系图谱.xml"
    if rel_file.exists():
        try:
            tree = ET.parse(rel_file)
            for r in tree.findall(".//relation"):
                s = r.get("source","")
                t = r.get("target","")
                tp = r.get("type","")
                d = (r.get("description") or "")[:80]
                parts.append("[关系] " + s + " -> " + t + " (" + tp + "): " + d)
        except: pass
    for cat in ["地点","物品","势力","背景"]:
        d = base / cat
        if d.exists():
            for f in sorted(d.glob("*.xml")):
                text = f.read_text(encoding="utf-8", errors="replace")
                desc = re.search(r'<description>(.*?)</description>', text, re.DOTALL)
                if desc:
                    parts.append("[" + cat + "] " + f.stem + ": " + desc.group(1).strip()[:80])
    return "\\n".join(parts) if parts else "（无设定数据）"

VariableResolver.COMPUTED_HANDLERS["novel_setting"] = _novel_setting

try:
    import handlers
except ImportError:
    pass"""

content = content.replace(old, new)
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile, os
py_compile.compile(filepath, doraise=True)
from variable_resolver import VariableResolver
os.environ['API_KEY'] = ''

print('novel_setting registered:', 'novel_setting' in VariableResolver.COMPUTED_HANDLERS)
if 'novel_setting' in VariableResolver.COMPUTED_HANDLERS:
    PROJ = r'C:\Users\Administrator\Documents\trae_projects\fangcun-write\projects\全家偷听心声'
    r = VariableResolver(PROJ)
    val = r.resolve('设定')
    lines = val.split('\n')
    seen = set()
    for line in lines:
        if line.startswith('['):
            seen.add(line.split(']')[0] + ']')
    print('类别:', seen)
    print('行数:', len(lines))
    for line in lines[:3]:
        print(' ', line[:80])
else:
    print('FAILED - novel_setting not registered')
