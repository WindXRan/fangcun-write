---
version: 9
changelog: 极致精简——风格由plot_guide引导，质量由unified_review兜底，write只负责创作
type: user
phase: write
description: 写章
required_vars: ["N", "新书名", "作者名", "源书名", "目标字数", "目标字数_min", "目标字数_max"]
optional_vars: ["女主名", "男主名"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-pro", "max_tokens": 8192, "reasoning_effort": "high", "temperature": 0.8}
---

写《{新书名}》第{N}章。

【plot_guide】projects/{作者名}/{源书名}/rewrites/{新书名}/guides/plot_{N}.md
【源文全文】projects/{作者名}/{源书名}/_cache/chapters/第{N}章.txt

按 plot_guide 的叙事策略和节拍创作。章名取 plot_guide 标注的，未标注则自拟。正文第一行写"第{N}章 [章名]"（不加#）。

字数：{目标字数}字（{目标字数_min}~{目标字数_max}）。

角色：女主={女主名}，男主={男主名}。

输出：projects/{作者名}/{源书名}/rewrites/{新书名}/chapters/ch_{N}.txt
