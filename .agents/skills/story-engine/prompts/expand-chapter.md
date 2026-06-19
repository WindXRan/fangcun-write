---
version: 3
changelog: 增强：加入plot_guide锚点+角色行为卡片约束+反AI检查
type: user
phase: postprocess
description: 扩写章节
required_vars: ["content", "orig_chars", "target_chars", "min_chars", "max_chars"]
optional_vars: ["plot_guide", "角色行为卡片", "世界观"]
system_prompt: system-generic.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---

你是专业网文写手。请扩写以下章节，增加内容使字数达到{target_chars}字左右。

【plot_guide 锚点】
{plot_guide}

【角色行为卡片】
{角色行为卡片}

【扩写要求】
1. 保持原有情节框架和人物关系，不可偏离 plot_guide
2. 增加细节描写（五感、环境、动作），用具体画面感代替抽象描述
3. 增加对话互动，但对话内容必须符合角色性格
4. 增加场景过渡，让情节衔接更自然
5. 不要增加新的情节线，不要偏离主线
6. 角色行为必须符合行为卡片，不可人设崩塌
7. 字数控制在{min_chars}~{max_chars}字

【反AI要求】
- 禁用：倏地/入目/紧了床单/她想起来了/她回忆道/这时/突然/然后/紧接着/她明白了/她意识到/必须/不得不/一下子/忽然/转眼间/只见/但见
- 句首多样，不连续2句人名开头
- 对话标签≥30%用动作替代"XX说/XX道"
- 不要以"窗外+植物+微小变化"结尾

【原文（{orig_chars}字）】
{content}

【输出格式】
直接输出扩写后的完整章节，不要解释，不要加任何前缀后缀。

