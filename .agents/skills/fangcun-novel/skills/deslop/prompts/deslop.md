---
version: 1
type: user
phase: deslop
description: 去AI味检测与修复
---

<instructions>
对以下文本进行AI痕迹检测，并根据模式进行处理。

**模式：** {mode}（detect / rewrite / edit）

**检测规则：**
1. 路标词（首先/其次/最后/总而言之）
2. 高频副词（微微/轻轻/淡淡/缓缓）
3. 空洞修饰词（深入/全面/有效/显著）
4. 模板句式（通过...的方式/在...的基础上）
5. 情绪形容词堆砌（温暖/感动/幸福）
6. 动作描写重复（点头/摇头/叹气/微笑）

**修复原则：**
- 保持原文意思不变
- 替换路标词为自然过渡
- 删除空洞修饰词
- 拆分过长的句子
- 增加口语化表达
</instructions>

<text>
{text}
</text>

<source_metrics>
源文AI痕迹数量：{src_ai_markers}
修复后AI痕迹数量应 ≤ 源文数量
</source_metrics>

<whitelist>
以下词汇不算AI痕迹（白名单）：
{whitelist}
</whitelist>
