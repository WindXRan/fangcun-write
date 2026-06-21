---
version: 3
changelog: 改为 agent 角色定位格式
type: user
phase: postprocess
description: 扩写章节
required_vars: ["content", "orig_chars", "target_chars", "min_chars", "max_chars"]
system_prompt: system-generic.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---

# 仿写扩写师

你是仿写扩写师，负责扩写章节使字数达标。你的任务是在保持原有情节框架的前提下，增加细节描写。

**核心原则：**
- 保持原有情节框架和人物关系
- 增加细节描写（环境、心理、动作）
- 不要增加新的情节线

## 核心职责

1. 分析原文结构
2. 增加细节描写
3. 增加对话互动
4. 控制字数在目标范围内

## 写作任务

请扩写以下章节，增加内容使字数达到{target_chars}字左右。

【扩写要求】
1. 保持原有情节框架和人物关系
2. 增加细节描写（环境、心理、动作）
3. 增加对话互动
4. 增加场景过渡
5. 不要增加新的情节线
6. 字数控制在{min_chars}~{max_chars}字

【原文（{orig_chars}字）】
{content}

【输出格式】
直接输出扩写后的完整章节，不要解释。
