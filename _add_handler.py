import sys, py_compile

filepath = r'c:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\fangcun-write\tools\variable_resolver.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

NL = '\\n'
NL2 = '\\n\\n'

handler_code = '''
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
    return "''' + NL + '''".join(parts) if parts else "（无设定数据）"

VariableResolver.COMPUTED_HANDLERS["novel_setting"] = _novel_setting
'''

old = 'import handlers\n'
content = content.replace(old, handler_code + '\n' + old)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

py_compile.compile(filepath, doraise=True)
print('OK')
