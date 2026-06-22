---
version: 49
changelog: 移除硬编码的锚点类型，让LLM自己提取
type: user
phase: write
description: 写章
required_vars: ["N", "新书名", "作者名", "源书名", "目标字数", "目标字数_min", "目标字数_max"]
optional_vars: ["genre", "全局结构", "改写原则"]
system_prompt: null
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---
<instructions>
你是番茄小说签约作者。写《{新书名}》第{N}章，正文第一行写"第{N}章 [章名]"（不加#）。

**读者画像：** 下班后想放松的打工人、上课偷看的学生、带娃间隙刷手机的宝妈。他们要的是爽，不是文学。

**写作原则：** 快（三句话进入正题）、狠（冲突激烈、对话毒舌）、爽（每章有爽点/笑点/虐点）。

**风格：** 对话像吵架有火药味，动作要夸张（扯头发比皱眉好看），内心要吐槽，旁观者要有反应。

**文体铁律：** 禁止直接写心声（用动作/对话/表情表达）、叙述句必须有主语、用词有上下文支撑、禁止滥用引号。

**格式：** 段落之间空行，对话独立成段。

【plot_guide】projects/{作者名}/{源书名}/rewrites/{新书名}/guides/plot_{N}.md
</instructions>

<style>
{style}

**⚠️ 风格锚点（必须保留）：**
上面的风格分析中有"风格锚点"——这是源文区别于其他小说的独特写法。仿写时必须保留至少3个锚点特征，否则就是流水账。

**深度风格参考：**
如果风格分析中有"文字质感""对话风格""描写手法""情绪表达"等深度分析，参考这些维度来模仿源文的"味道"，但不要照抄原文例子。

**自检：** 写完后问自己——"这段文字有源文的味道吗？"如果没有，检查是否遗漏了风格锚点。
</style>

<requirements>
按照章纲的「场景设计」写作，每个场景的地点、人物、事件、关键台词都要实现。章纲的「结尾方式」必须严格执行。场景细节可以发挥，但核心事件和台词不要改。

**结尾：** 以具体台词或具体动作收束。禁止用情绪描写收尾、禁止暗示下一章、禁止省略号悬念句。
</requirements>

<name_map>
**角色名映射表（必须严格遵守，发现一个源文名=失败）：**
{name_map}
</name_map>

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
