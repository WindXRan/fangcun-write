---
version: 52
changelog: 纯task，不注入变量
type: task
phase: write
description: 写章
system_prompt: agent.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---
<task>
写《{新书名}》第{N}章。

按章纲的场景设计写作，每个场景的地点、人物、事件、关键台词都要实现。
章纲的结尾方式必须严格执行。
场景细节可以发挥，但核心事件和台词不要改。
</task>

