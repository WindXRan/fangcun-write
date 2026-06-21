---
version: 6
changelog: 修复变量名
type: user
phase: postprocess
description: 精简超字数章
required_vars: ["目标字数", "content", "N", "N03d"]
system_prompt: null
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---

精简下面的章节到 **{目标字数}个汉字** 以内。

**删减策略**：
1. 重复描写 → 删掉
2. 过度修饰 → 删掉（"微微""轻轻""缓缓""淡淡""不由得"）
3. 内心独白已用动作表达 → 删独白
4. 过渡描写 → 压缩
5. 不影响剧情的环境描写 → 删减

**保留**：所有关键对话、核心剧情转折、角色性格展示。

**绝对禁止**：
- ❌ 改动角色名（所有人名必须原样保留）
- ❌ 改动对话内容（只删不改）
- ❌ 添加新内容（只删不加）

**输出**：只输出精简后的全文，不加任何说明。

【原文】
{content}
