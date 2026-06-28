import re, py_compile

filepath = r'c:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\fangcun-write\tools\variable_resolver.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Simple approach: strip XML structure but keep tag names as labels
# <core_event>xxx</core_event> → core_event: xxx
# <setup><content>xxx</content><emotion>yyy</emotion></setup> → content: xxx, emotion: yyy

new_func = '''def _simplify_xml(raw: str) -> str:
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
    return '\\n'.join(lines)''' + '\n\n'

# Find the old _simplify_xml or _clean_xml function and replace
for old_name in ['_simplify_xml', '_clean_xml']:
    idx = content.find('def ' + old_name)
    if idx >= 0:
        end = content.find('\ndef ', idx + 1)
        if end < 0:
            end = content.find('\nclass ', idx + 1)
        if end < 0:
            end = content.find('\n# ', idx + 1)
        if end < 0:
            end = len(content)
        content = content[:idx] + new_func + content[end:]
        print(f'replaced {old_name}')
        break

# Also add the _fmt_tag helper right before _simplify_xml
fmt_tag = '''def _fmt_tag(m):
    """<tag attr="x">inner</tag> → tag: inner（内层有标签时展平为子项）"""
    tag = m.group(1).split()[0]
    inner = m.group(2).strip()
    # 内层有标签时递归
    return tag + ':\\n' + _indent(inner) if '<' in inner else tag + ': ' + inner


def _indent(text):
    """给多行文本加缩进"""
    return '\\n'.join('  ' + l for l in text.split('\\n'))


'''
# Insert helper functions
insert_point = content.find('def _simplify_xml')
if insert_point >= 0:
    content = content[:insert_point] + fmt_tag + content[insert_point:]
    print('inserted helpers')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

py_compile.compile(filepath, doraise=True)
print('OK - verified')
