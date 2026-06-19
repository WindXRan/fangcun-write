---
version: 2
type: user
phase: open_book_concept
description: 开书 - 精简索引生成（结构锁定）
required_vars: ["作者名", "源书名", "新书名", "源文分析"]
system_prompt: system-generic.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---

基于源文分析，为《{新书名}》生成精简索引。

## 源文分析（已锁定，不可更改）

{源文分析}

## 输出内容

1. **定位**（一句话）：新书的题材+受众（必须与源文同赛道）
2. **策略**（一句话）：仿写的核心差异化（换什么壳、保什么骨）
3. **卖点**（一句话）：与源文同构的核心吸引力

## 自查清单（生成后内部校验，不输出）

- [ ] 定位与源文同赛道
- [ ] 策略明确说明"换壳保骨"
- [ ] 卖点与源文同构
