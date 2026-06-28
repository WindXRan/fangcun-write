import re

filepath = r'c:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\fangcun-write\tools\variable_resolver.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and fix _simplify_xml function
old_simplify = """def _simplify_xml(raw: str) -> str:
    \"\"\"把带标签的 XML 内容压平为 LLM 易读的文本。
    只保留标签名作为字段名，去掉嵌套标签，去掉属性。
    例: <guide chapter=\"1\"><core_event>xxx</core_event></guide>
    → core_event: xxx\"\"\"
    import re
    # 剥离 XML 声明和注释
    raw = re.sub(r'<\?xml[^>]*\?>', '', raw)
    raw = re.sub(r'<!--.*?-->', '', raw, flags=re.DOTALL)
    # 把 <tag>text</tag> 压成 "tag: text"
    def _flatten(m):
        tag = m.group(1)
        inner = m.group(2).strip()
        # 如果内层还有标签，递归压平
        inner = _flatten_xml(inner)
        # 多行内容用缩进
        if '\\n' in inner:
            return tag + ': \\n' + '\\n'.join('  ' + l for l in inner.split('\\n'))
        return tag + ': ' + inner
    # 递归压平
    def _flatten_xml(text):
        # 从最内层开始替换
        prev = None
        while prev != text:
            prev = text
            text = re.sub(r'<([a-zA-Z_][^>]*)>(.*?)</\\1>', _flatten, text, flags=re.DOTALL)
        return text
    raw = _flatten_xml(raw)
    # 清理残余标签
    raw = re.sub(r'<[^>]+>', '', raw)
    raw = re.sub(r'\\n{3,}', '\\n\\n', raw)
    return raw.strip()"""

new_simplify = """def _simplify_xml(raw: str) -> str:
    \"\"\"剥掉 XML 标签，只留可读文本。\"\"\"
    # 剥离 XML 声明和注释
    raw = re.sub(r'<\\?xml[^>]*\\?>', '', raw)
    raw = re.sub(r'<!--.*?-->', '', raw, flags=re.DOTALL)
    # 去掉所有标签
    raw = re.sub(r'<[^>]+>', '', raw)
    # 清理空行
    lines = [l.strip() for l in raw.split('\\n')]
    raw = '\\n'.join(l for l in lines if l)
    return raw.strip()"""

if old_simplify in content:
    content = content.replace(old_simplify, new_simplify)
    print('replaced simplify')
else:
    # Check if the old _clean_xml is still there
    if 'def _clean_xml' in content:
        print('_clean_xml still present, will replace')
        idx = content.find('def _clean_xml')
        end = content.find('\ndef ', idx + 1)
        if end < 0:
            end = content.find('\nclass ', idx + 1)
        if end < 0:
            end = len(content)
        old_block = content[idx:end]
        content = content.replace(old_block, new_simplify)
        print('replaced _clean_xml')

# Update references
content = content.replace('_clean_xml(f.read_text(encoding', '_simplify_xml(f.read_text(encoding')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
import py_compile
py_compile.compile(filepath, doraise=True)
print('OK - verified')
