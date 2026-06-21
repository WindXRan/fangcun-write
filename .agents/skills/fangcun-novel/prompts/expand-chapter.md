---
version: 5
changelog: 迁移到XML标签格式
type: user
phase: postprocess
description: 扩写章节
required_vars: ["content", "orig_chars", "target_chars", "min_chars", "max_chars"]
system_prompt: null
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---

<instructions>
扩写以下章节，增加内容使字数达到{target_chars}字左右。
</instructions>

<requirements>
**扩写要求**：
1. 保持原有情节框架和人物关系
2. 增加细节描写（环境、心理、动作）
3. 增加对话互动
4. 不要增加新的情节线
5. 字数控制在{min_chars}~{max_chars}字
</requirements>

<restrictions>
**绝对禁止**：
- ❌ 改动角色名（所有人名必须原样保留）
- ❌ 改动已有对话（只加不改）
- ❌ 删除已有内容（只加不删）
</restrictions>

<original>
【原文（{orig_chars}字）】
{content}
</original>

<output_format>
【输出格式】
直接输出扩写后的完整章节，不要解释。
</output_format>
