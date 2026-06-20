---
name: expand
version: 1
description: 扩写章节
type: user
phase: expand
system_prompt: system-generic.md
---

请扩写以下章节，目标字数约{target_chars}字。

## 扩写要求

1. **保持原有情节框架和人物关系**
2. **增加细节描写**（五感、环境、动作）
3. **增加对话互动**
4. **增加场景过渡**
5. **不要增加新的情节线**
6. **字数控制**：{target_chars}字左右（±10%）

## 原文（{orig_chars}字）

{content}

## 输出格式

直接输出扩写后的完整章节，不要解释，不要加任何前缀后缀。
