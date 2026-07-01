p = '.agents/skills/fangcun-write/SKILL.md'
content = open(p, encoding='utf-8').read()
content = content.replace('| `chat-assistant` | 通用创作对话 | 默认 |\n', '')

# Remove volume-analysis from tool_executor.py
p2 = '.agents/skills/fangcun-write/tools/tool_executor.py'
c2 = open(p2, encoding='utf-8').read()
# volume-analysis is in SIMPLE_PRESETS
c2 = c2.replace('        "volume-analysis",\n', '')
# Remove chat-assistant from SIMPLE_PRESETS
c2 = c2.replace('        "chat-assistant",\n', '')

open(p, 'w', encoding='utf-8').write(content)
open(p2, 'w', encoding='utf-8').write(c2)
print('done')
