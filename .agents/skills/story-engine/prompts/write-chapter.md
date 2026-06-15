---
version: 7
changelog: 反面规则改为对标正面结构化输出；正面标注"本章特例"不仿
type: user
phase: write
description: 写章
required_vars: ["N", "新书名", "作者名", "源书名", "目标字数", "目标字数_min", "目标字数_max"]
optional_vars: ["genre", "女主名", "男主名", "文笔指纹"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-flash", "max_tokens": 4096, "reasoning_effort": "low", "temperature": 0.8}
---
写《{新书名}》第{N}章。正文第一行写"第{N}章 [章名]"（不加#）。章名取 plot_guide 中标注的，未标注则自拟。

按 plot_guide 节拍的情绪功能定位创作全新内容，不是改写源文。

【plot_guide】projects/{作者名}/{源书名}/rewrites/{新书名}/guides/plot_{N}.md

## 本章源文风格指纹

{文笔指纹}

---

## 写作要求
- 按节拍情绪功能定位写，不逐段对应源文结构
- 前300字直接进场景/冲突/悬念；章末留钩子
- 选一个节拍放大写，这就是本章**记忆点**
- 时间跳跃在开头1-2句交代

## 反AI检测（朱雀防线）
- **句长交错**：长短句交替（5字短句 ↔ 30字以上长句），不连续2句同长度
- **代词替换**：同一人物连续出现时，交替用名字/身份/外号/零代词，不连续3次用他/她
- **词汇多样**：同一段落内不重复使用同一形容词/动词，关键词隔段落地才复用
- **句式变换**：叙述/对话/心理/动作交替推进，不连续3句同句式

## 角色名
女主={女主名}，男主={男主名}。

## 字数
目标 {目标字数} 字（{目标字数_min}~{目标字数_max}）。

## 输出路径
projects/{作者名}/{源书名}/rewrites/{新书名}/chapters/ch_{N}.txt
