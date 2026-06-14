---
name: style-analyze
description: 单章文笔风格分析
system_prompt: system-generic.md
defaults:
  model: deepseek-v4-flash
  max_tokens: 1024
  reasoning_effort: low
  temperature: 0.3
---

分析这一章的文笔特征。3-5 句话，只描述风格不评价好坏。

维度：
- 句式节奏是急促还是舒缓
- 对话占比和写法习惯
- 情绪渲染方式（直抒还是克制）
- 这章独有的标志性写法和表达习惯

算法参考（不要复述数字）: {style_anchors}

章节内容:
{chapter_text}
