---
version: 8
changelog: 纯task，不注入变量
type: task
phase: postprocess
description: 润色章节
system_prompt: base_agent.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---
<task>
让仿写读起来更像源文的风格，但绝对不能抄源文的内容。

1. 调整节奏：句子平均长度接近源文
2. 调整对话比例：接近源文的对话占比
3. 调整段落长度：接近源文的段落平均长度
4. 去掉AI味：删除"仿佛""似乎""不禁""心中涌起""顿了顿""沉默了片刻"
5. 让心声更自然：不要直接写"她想""她觉得"，用动作或对话表达
6. 让对话更口语化：加语气词

**禁止**：抄源文表达、改变情节/人物/对话内容、改动角色名、增删情节。
</task>
