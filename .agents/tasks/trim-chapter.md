---
version: 11
changelog: 文件引用模式
type: task
phase: postprocess
description: 精简超字数章
system_prompt: agent.md
defaults: {"reasoning_effort": "low", "temperature": 0.8}
---
<task>
把文章砍到目标字数。必须删掉足够的字数。

**砍法**（直接删，不要重写）：
1. 删掉"微微""轻轻""缓缓""淡淡""不由得""不禁""仿佛""似乎"
2. 删掉重复的情绪描写
3. 删掉已用动作表达的内心独白
4. 压缩过渡描写
5. 删掉不影响剧情的环境描写
6. 删掉不重要的对话轮次
7. 删掉旁观者的不重要反应

**保留**：关键对话、核心剧情转折、角色性格展示。

**禁止**：改动角色名、改动对话内容、添加新内容、重写段落。
</task>

原文：
【原文】{rewrites_dir}/chapters/ch_{N03d}.txt
