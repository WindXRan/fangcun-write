---
version: 50
changelog: Agent/Task架构，通用规则移到agent.md
type: task
phase: write
description: 写章
required_vars: ["N", "新书名", "作者名", "源书名", "目标字数", "目标字数_min", "目标字数_max"]
optional_vars: ["genre", "全局结构", "改写原则"]
system_prompt: agent.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---
<task>
写《{新书名}》第{N}章。

【plot_guide】projects/{作者名}/{源书名}/rewrites/{新书名}/guides/plot_{N}.md
</task>

<style>
{style}
</style>

<requirements>
按照章纲的「场景设计」写作，每个场景的地点、人物、事件、关键台词都要实现。章纲的「结尾方式」必须严格执行。场景细节可以发挥，但核心事件和台词不要改。
</requirements>

<characters>
{characters}
</characters>

<word_count>
**目标字数：{目标字数}字（{目标字数_min}~{目标字数_max}）**
</word_count>

<global_context>
<structure>
{structure}
</structure>

<principles>
{principles}
</principles>
</global_context>
