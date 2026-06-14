---
version: 5
changelog: 精简：去重system规则、砍自检清单、merge小节
type: user
phase: write
description: 写章
required_vars: ["N", "新书名", "作者名", "源书名", "目标字数", "目标字数_min", "目标字数_max"]
optional_vars: ["genre", "女主名", "男主名", "文笔锚点", "文笔风格"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-flash", "max_tokens": 4096, "reasoning_effort": "low", "temperature": 0.8}
---
写《{新书名}》第{N}章。正文第一行写"第{N}章 [章名]"（不加#）。章名取 plot_guide 中标注的，未标注则自拟。

**你不接触源文。** plot_guide 已将源文抽象为节拍表，按节拍创作全新内容，不是改写源文。

【plot_guide】projects/{作者名}/{源书名}/rewrites/{新书名}/guides/plot_{N}.md

## 本章写作规则（源文风格指纹）

**锚点**: {文笔锚点}

**正面（必须做到）:**
{文笔风格}

**反面（必须避免）:**
- 不能写成 AI 味的平铺直叙（句长均匀、每段 3 句、引号外全是叙述）
- 不能偏离上述锚点太远（句长/对话比/段长/标点风格对齐）
- 不能丢失上述正面规则中的写法特征

---

## 写作要求

1. 按 plot_guide 节拍的情绪功能定位写，**不逐段对应源文结构**
2. 每章至少一个**记忆点**——读者看完能记住的画面/对话/情绪/反转
3. 选一个节拍放大写，给足细节，这就是记忆点
4. 前 300 字必须有钩子，直接进场景/冲突/悬念
5. 章末留钩子引导下一章
6. 时间跳跃在开头用 1-2 句交代
7. 角色行为对齐 plot_guide 标注的心理阶段

## 角色名

女主={女主名}，男主={男主名}。禁止使用源文人名。

## 字数

目标 {目标字数} 字（{目标字数_min}~{目标字数_max}）。

## 输出

【输出】projects/{作者名}/{源书名}/rewrites/{新书名}/chapters/ch_{N}.txt
