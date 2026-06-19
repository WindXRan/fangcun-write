---
version: 1
type: user
phase: open_book_concept
description: 开书 - 精简索引生成
required_vars: ["作者名", "源书名", "新书名", "源文分析"]
system_prompt: system-generic.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---

基于源文分析，为《{新书名}》生成精简索引。

## 源文分析（已锁定，不可更改）

{源文分析}

## 输出内容

1. **定位**（一句话）
2. **策略**（一句话）
3. **卖点**（一句话）

## 自查清单（生成后内部校验，不输出）

- [ ] 定位一句话，明确题材+受众
- [ ] 策略一句话，明确差异化方向
- [ ] 卖点一句话，体现核心吸引力
