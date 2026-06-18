---
version: 2
changelog: 修复乱码，重新创建
type: user
phase: postprocess
description: 润色章节
required_vars: ["content", "min_chars", "max_chars"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-pro", "temperature": 0.8}
---

你是专业网文写手。请润色以下章节，提升文笔质量。

【润色要求】
1. 不改变情节、人物、对话内容
2. 删除AI痕迹（"仿佛"、"似乎"、"不禁"、"心中涌起"、"顿了顿"、"停了停"、"愣了一下"、"沉默了片刻"等）
3. 增加细节描写（五感、环境、动作）
4. 优化句式，避免排比句连续超过3句；对话标签至少30%用动作替代"XX说/XX道"
5. 对话更自然，像真人说话；同一角色在不同场景的情绪反应不能相同
6. 字数控制在原文±10%以内（{min_chars}~{max_chars}字）

【原文】
{content}

【输出格式】
直接输出润色后的完整章节，不要解释。
