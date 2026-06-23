---
version: 53
changelog: 文件引用模式，不依赖代码注入
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

目标字数：{目标字数}字（{目标字数_min}~{目标字数_max}）
</task>

<plot_guide>
【plot_guide】{rewrites_dir}/guides/plot_{N}.md
</plot_guide>

<style>
【style】{rewrites_dir}/../../_cache/styles/style_{N03d}_llm.md
</style>

<characters>
{characters}
</characters>

<structure>
【structure】{rewrites_dir}/../../_cache/styles/structure_{N03d}.md
</structure>

<principles>
【principles】{rewrites_dir}/concept.md
</principles>
