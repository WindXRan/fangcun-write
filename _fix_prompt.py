import re, py_compile

filepath = r'c:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\fangcun-write\tools\variable_resolver.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace _simplify_xml with a better version
old_simplify = '''def _simplify_xml(raw: str) -> str:
    """剥掉 XML 结构，留可读文本。标签名保留为行首标签。"""
    # 剥声明和注释
    raw = re.sub(r'<\\?xml[^>]*\\?>', '', raw)
    raw = re.sub(r'<!--.*?-->', '', raw, flags=re.DOTALL)
    # <tag>text</tag> → tag: text
    prev = None
    while prev != raw:
        prev = raw
        raw = re.sub(r'<([a-zA-Z_][^>]*)>(.*?)<\\/\\1>', _fmt_tag, raw, flags=re.DOTALL)
    # 清理残余标签
    raw = re.sub(r'<[^>]+>', '', raw)
    lines = [l.strip() for l in raw.split('\\n') if l.strip()]
    return '\\n'.join(lines)'''

new_simplify = '''def _simplify_xml(raw: str) -> str:
    """剥掉 XML 标签，保留内容。标签名转为行首标签。"""
    # 剥声明和注释
    raw = re.sub(r'<\\?xml[^>]*\\?>', '', raw)
    raw = re.sub(r'<!--.*?-->', '', raw, flags=re.DOTALL)
    # 自闭合标签: <tag /> → 删除
    raw = re.sub(r'<[^>]+/>', '', raw)
    # <tag>text</tag> → tag: text（不嵌套）
    prev = None
    while prev != raw:
        prev = raw
        raw = re.sub(r'<([a-zA-Z_][^>]*)>(.*?)<\\/\\1>', _fmt_tag, raw, flags=re.DOTALL)
    # 清理残余标签
    raw = re.sub(r'<[^>]+>', '', raw)
    # 清理空行和首尾空格
    lines = [l.strip() for l in raw.split('\\n') if l.strip()]
    return '\\n'.join(lines)


# ─── 套路分析精简器：仿写模式只提取节奏节点和情绪 ───

def _extract_rhythm(raw: str) -> str:
    """从套路分析 XML 中只提取节奏节点和情绪模板，去掉其他模块。"""
    import re
    parts = []
    # 提取 rhythm_nodes 区块
    m = re.search(r'<rhythm_nodes>(.*?)</rhythm_nodes>', raw, re.DOTALL)
    if m:
        nodes = _simplify_xml(m.group(0))
        parts.append('【节奏节点】\\n' + nodes)
    # 提取 emotional_template
    m = re.search(r'<emotional_template>(.*?)</emotional_template>', raw, re.DOTALL)
    if m:
        et = _simplify_xml(m.group(0))
        parts.append('【情绪模板】\\n' + et)
    # 提取 genre 定位
    m = re.search(r'<genre[^>]*>(.*?)<\\/genre>', raw, re.DOTALL)
    if m:
        parts.append('题材: ' + _simplify_xml(m.group(1)))
    return '\\n\\n'.join(parts) if parts else _simplify_xml(raw)''' + '\n\n\n'

# Find and replace
idx = content.find('def _simplify_xml')
if idx >= 0:
    end = content.find('\ndef ', idx + 1)
    if end < 0:
        end = len(content)
    content = content[:idx] + new_simplify + content[end:]
    print('replaced _simplify_xml')
else:
    print('_simplify_xml not found')

# Update _source_pattern_analysis to use _extract_rhythm instead of _simplify_xml
content = content.replace(
    'return _simplify_xml(f.read_text(encoding',
    'return _extract_rhythm(f.read_text(encoding'
)
content = content.replace(
    '_extract_rhythm(f.read_text(encoding',
    '_extract_rhythm(f.read_text(encoding'
)

# Apply _simplify_xml to ALL .xml file reads in computed handlers
# Find the auto-loader section where .xml files are registered
old_loader = '''        if _var not in VariableResolver.COMPUTED_HANDLERS:
            @VariableResolver.register_computed(_var)
            def _loader(self, p=_f):
                try: return p.read_text(encoding='utf-8')
                except: return ""'''

new_loader = '''        if _var not in VariableResolver.COMPUTED_HANDLERS:
            @VariableResolver.register_computed(_var)
            def _loader(self, p=_f):
                try:
                    text = p.read_text(encoding='utf-8')
                    if p.suffix == '.xml':
                        text = _simplify_xml(text)
                    return text
                except: return ""'''

count = content.count(old_loader)
if count > 0:
    content = content.replace(old_loader, new_loader)
    print(f'applied simplify to {count} template loaders')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
py_compile.compile(filepath, doraise=True)
print('OK')
