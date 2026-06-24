---
version: 59
changelog: 删除所有硬编码规则，回归纯指导
type: task
phase: write
description: 写章
system_prompt: agent.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---
<task>
写《{新书名}》第{N}章。目标字数：2000-3000字。
</task>

<style>
【style】{rewrites_dir}/../../_cache/styles/style_{N03d}_llm.md

**风格锚点（必须保留）：**
上面的风格分析中有"风格锚点"——这是源文区别于其他小说的独特写法。仿写时必须保留至少3个锚点特征，否则就是流水账。

**深度风格参考：**
如果风格分析中有"文字质感""对话风格""描写手法""情绪表达"等深度分析，参考这些维度来模仿源文的"味道"。
</style>

<requirements>
按照章纲的「场景设计」写作，每个场景的地点、人物、事件、关键台词都要实现。章纲的「结尾方式」必须严格执行。

**整体基调与源文一致：**
本章的基调必须与源文的整体风格保持一致。源文是轻松吐槽流→你不能写成沉重现实。读style分析时重点看"叙事基调"和"情绪基调"。

**结尾：** 以具体台词或具体动作收束。禁止用情绪描写收尾、禁止省略号悬念句。
</requirements>

<name_map>
## 角色名铁律

name_map 中从左到右是 源文名→新名。全文所有角色必须使用新名（箭头右侧的名字），出现任何一个源文名=本章作废重写。

主角名只有一个，从 name_map 中查找。主角名从头到尾固定不变，禁止任何变体。

{name_map}
</name_map>

<characters>
{characters}
</characters>

<plot_guide>
【plot_guide】{rewrites_dir}/guides/plot_{N}.md
</plot_guide>

<principles>
【principles】{rewrites_dir}/concept.md
</principles>
