import sys
filepath = r'c:\Users\Administrator\Documents\trae_projects\fangcun-write\.agents\skills\fangcun-write\tools\chapter_summary.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = 'FIELDS = ["核心事件", "出场角色", "情绪基调", "冲突类型"]'
new = 'FIELDS = ["核心事件", "关键转折", "出场角色", "情绪基调", "冲突类型"]'
if old in content:
    content = content.replace(old, new)
    print('updated FIELDS')

old = """    sys_prompt = \"\"\"你是有经验的网文编辑。读一章正文，提取4个字段：
- 核心事件：一句话概括本章最重要的剧情推进（15字内）
- 出场角色：本章实际出场的主要角色名，逗号分隔
- 情绪基调：读者读完本章的情绪变化，如\"压抑→爽→期待\"
- 冲突类型：本章核心冲突类型，如\"身份冲突/生存冲突/信息差冲突/打脸\"

只输出这4个字段，每行一个。不要多余内容。\"\"\""""

new = """    sys_prompt = \"\"\"你是有经验的网文编辑。读一章正文，提取5个字段：
- 核心事件：一句话概括本章最重要的剧情推进（25字内）
- 关键转折：本章从开头到结尾发生了什么转变（情绪/局势/认知/关系）
- 出场角色：本章实际出场的主要角色名，逗号分隔
- 情绪基调：读者读完本章的情绪变化，如\"压抑→爽→期待\"
- 冲突类型：本章核心冲突类型，如\"身份冲突/生存冲突/信息差冲突/打脸\"

只输出这5个字段，每行一个。不要多余内容。\"\"\""""

if old in content:
    content = content.replace(old, new)
    print('updated sys_prompt')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile(filepath, doraise=True)
print('OK')
