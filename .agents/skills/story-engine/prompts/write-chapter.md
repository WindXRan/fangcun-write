---
version: 7
changelog: 反面规则改为对标正面结构化输出；正面标注"本章特例"不仿
type: user
phase: write
description: 写章
required_vars: ["N", "新书名", "作者名", "源书名", "目标字数", "目标字数_min", "目标字数_max"]
optional_vars: ["genre", "女主名", "男主名", "文笔指纹", "角色行为卡片"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-pro", "max_tokens": 8192, "reasoning_effort": "high", "temperature": 0.8}
---
写《{新书名}》第{N}章。正文第一行写"第{N}章 [章名]"（不加#）。章名取 plot_guide 中标注的，未标注则自拟。

按 plot_guide 节拍的情绪功能定位创作全新内容，不是改写源文。

【plot_guide】projects/{作者名}/{源书名}/rewrites/{新书名}/guides/plot_{N}.md

## 本章硬性规则（必须做到，缺一不可）

{文笔指纹}

**写作**: 按节拍情绪定位写，不逐段对应源文。前300字进场景/悬念。选一个节拍放大写作为记忆点。章末留钩子。时间跳跃开头1-2句交代。

**反AI**: 句长极端交替(5字↔50字), 段尾极短句或省略号, 代词不连续3次同字, 同段不重复形容词, 句式不连续3句同类型。

**角色行为约束（本章出现的角色必须对齐以下卡片）:**
{角色行为卡片}

## 角色名
女主={女主名}，男主={男主名}。

## 字数
目标 {目标字数} 字（{目标字数_min}~{目标字数_max}）。

## 输出路径
projects/{作者名}/{源书名}/rewrites/{新书名}/chapters/ch_{N}.txt
