---
name: style-analyze
version: 2
changelog: 结构化输出模板（句法/词汇/对话/反面），每条为可执行指令
description: 提取可复制的写法特征（正面仿写+反面避坑）
system_prompt: system-generic.md
defaults:
  model: deepseek-v4-flash
  max_tokens: 4096
  reasoning_effort: low
  temperature: 0.3
---

输出本章风格规则，每条是**可执行的仿写指令**，附源文例句。

句法: 句长控制在X-Y字(中位Z) 句首以__开头为主 短句占比X%
词汇: 代词密度X/千字 常用词:[词1,词2] 书面对口语比例
对话: 引号外叙述占比X% 说vs道vs动作代比例

反面(本章特例+AI易走样):
- 本章[某特征]是因情节需要，全书非常用
- [AI最容易偏离的1-2方向]

锚点: {style_anchors}
章节: {chapter_text}
