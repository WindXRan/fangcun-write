---
version: 4
changelog: 续写模式润色（无源文对比）
type: user
phase: postprocess
description: 润色章节
required_vars: ["content", "min_chars", "max_chars"]
system_prompt: system.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---

你是专业网文写手。请润色以下章节，提升文笔质量。

## 润色要求

1. **不改变情节、人物、对话内容**
2. **删除AI痕迹**（"仿佛""似乎""不禁""心中涌起""顿了顿""沉默了片刻"等），用更自然的表达替代
3. **让心声更自然**：不要直接写"她想""她觉得"，用动作或对话来表达情绪
4. **让对话更像真人说话**：加点语气词（呢、啊、吧、嘛），让对话更口语化
5. **增加细节描写**（五感、环境、动作）
6. **优化句式**，避免排比句连续超过3句
7. **对话标签**至少30%用动作替代"XX说/XX道"
8. **字数控制**：原文±10%（{min_chars}~{max_chars}字）

## 你绝对不能做的事

- ❌ 改变情节、人物、对话内容
- ❌ 增加或删除情节

## 原文

{content}

## 输出

直接输出润色后的完整章节，不要解释。
