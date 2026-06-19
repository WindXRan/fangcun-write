---
version: 3
changelog: 增强：加入plot_guide锚点+角色行为卡片约束+反AI检查
type: user
phase: postprocess
description: 润色章节
required_vars: ["content", "min_chars", "max_chars"]
optional_vars: ["plot_guide", "角色行为卡片", "世界观"]
system_prompt: system-generic.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---

你是专业网文写手。请润色以下章节，提升文笔质量。

【plot_guide 锚点】
{plot_guide}

【角色行为卡片】
{角色行为卡片}

【润色要求】
1. 不改变情节、人物、对话内容，只改文笔
2. 删除AI痕迹（"仿佛"、"似乎"、"不禁"、"心中涌起"、"顿了顿"、"停了停"、"愣了一下"、"沉默了片刻"等）
3. 增加细节描写（五感、环境、动作），用具体画面感代替抽象描述
4. 优化句式，避免排比句连续超过3句
5. 对话标签至少30%用动作替代"XX说/XX道"
6. 对话更自然，像真人说话
7. 同一角色在不同场景的情绪反应不能相同，必须符合行为卡片
8. 字数控制在原文±10%以内（{min_chars}~{max_chars}字）

【反AI要求】
- 禁用：倏地/入目/紧了床单/她想起来了/她回忆道/这时/突然/然后/紧接着/她明白了/她意识到/必须/不得不/一下子/忽然/转眼间/只见/但见
- 句首多样，不连续2句人名开头
- 不要以"窗外+植物+微小变化"结尾
- "顿了顿/停了停"全章不超过1次

【原文】
{content}

【输出格式】
直接输出润色后的完整章节，不要解释，不要加任何前缀后缀。

