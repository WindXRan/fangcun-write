import re, py_compile

filepath = r'c:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\fangcun-write\tools\variable_resolver.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. File-path resolver: apply _simplify_xml to .xml files
old_path = """                    else:
                        val = p.read_text(encoding='utf-8')
                        self._cache[var_name] = val
                        return val"""

new_path = """                    else:
                        val = p.read_text(encoding='utf-8')
                        if p.suffix == '.xml':
                            val = _simplify_xml(val)
                        self._cache[var_name] = val
                        return val"""

if old_path in content and new_path not in content:
    content = content.replace(old_path, new_path)
    print('patched file-path resolver')
else:
    print('file-path resolver: already patched or not found')

# 2. 关联章纲: apply _simplify_xml
old_guide = """parts.append(f"---第{i}章章纲---\\n{p.read_text(encoding='utf-8')}")"""
new_guide = """parts.append(f"---第{i}章章纲---\\n{_simplify_xml(p.read_text(encoding='utf-8'))}")"""

if old_guide in content:
    content = content.replace(old_guide, new_guide)
    print('patched 关联章纲')
else:
    print('关联章纲: not found')

# 3. 关联章节 (previous chapter text): already strips tags at line 732
# 4. 本章正文 (current chapter): already strips tags at line 757

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
py_compile.compile(filepath, doraise=True)
print('OK')
