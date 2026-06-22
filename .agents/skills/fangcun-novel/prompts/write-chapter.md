---
version: 45
changelog: 按照章纲场景写作，不再自行设计
type: user
phase: write
description: 写章
required_vars: ["N", "新书名", "作者名", "源书名", "目标字数", "目标字数_min", "目标字数_max"]
optional_vars: ["genre", "全局结构", "改写原则"]
system_prompt: system-generic.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---
<instructions>
写《{新书名}》第{N}章。正文第一行写"第{N}章 [章名]"（不加#）。

【plot_guide】projects/{作者名}/{源书名}/rewrites/{新书名}/guides/plot_{N}.md
</instructions>

<style>
{style}
</style>

<requirements>
**按照章纲的「场景设计」写作**，每个场景的地点、人物、事件、关键台词都要实现。

**章纲的「结尾方式」必须严格执行**，最后一句直接用章纲给的，或在此基础上调整。

**场景细节可以发挥**：章纲给的是骨架，你可以补充环境描写、人物表情、过渡动作，但核心事件和台词不要改。

**结尾规则（严格执行）：**
- 以**具体台词**或**具体动作**收束，不要用旁白总结情绪
- 禁止以下结尾模式：
  - "他笑了笑，心里暖暖的"
  - "嘴角怎么都压不下去"
  - "她暗暗下定决心"
  - "这一夜，他想了很多"
  - "他不知道，这只是个开始"
  - 任何暗示"接下来会发生什么"的句子
- 结尾不需要"钩子"，读者自然会翻下一章
</requirements>

<name_map>
**必须使用新名字，绝对不能使用源文名字！**

**角色名映射表（必须严格遵守）：**
{name_map}

**铁律：**
1. 角色卡里的名字如果有对应的新名，必须用新名
2. 写完后逐个检查每个角色名，确认都在"新名"列
3. 发现一个源文名 = 本次输出失败，必须重写
</name_map>

<characters>
{characters}
</characters>

<word_count>
**目标字数：{目标字数}字（{目标字数_min}~{目标字数_max}）**

**写完后必须检查字数，如果超出范围，必须删减或补充！**
</word_count>

<global_context>
<structure>
{structure}
</structure>

<principles>
{principles}
</principles>
</global_context>

<output_path>
projects/{作者名}/{源书名}/rewrites/{新书名}/chapters/ch_{N}.txt
</output_path>

<checklist>
- [ ] 字数在目标范围内
- [ ] 章纲的每个场景都实现了（地点、人物、事件、关键台词）
- [ ] 结尾方式与章纲一致（最后一句是具体台词或动作）
- [ ] 角色名全部正确
- [ ] 风格与源文一致
</checklist>
