---
version: 2
changelog: 从fangcun-novel同步
type: user
phase: postprocess
description: 扩写章节
required_vars: ["content", "orig_chars", "target_chars", "min_chars", "max_chars"]
system_prompt: system.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---

你是专业网文写手。请扩写以下章节，增加内容使字数达到{target_chars}字左右。

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
