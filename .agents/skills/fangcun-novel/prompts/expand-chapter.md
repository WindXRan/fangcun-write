---
version: 6
changelog: 纯task，不注入变量
type: task
phase: postprocess
description: 扩写章节
system_prompt: base_agent.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---
<task>
扩写章节，增加内容使字数达到目标。

**扩写方法**：
1. 增加环境描写、心理描写、动作细节
2. 增加对话互动
3. 保持原有情节框架和人物关系
4. 不增加新情节线

**禁止**：改动角色名、改动已有对话、删除已有内容。
</task>
