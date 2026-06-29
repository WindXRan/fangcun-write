import sys
filepath = r'c:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\fangcun-write\tools\tool_executor.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '"volume-outline": "正文/卷纲/卷纲.xml"'
new = '"volume-outline": f"正文/卷纲/第{args.get("volume_number", args.get("vol", 1))}卷.xml"'

content = content.replace(old, new)
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile(filepath, doraise=True)
print('OK')
