---
name: postfix
version: 1.0.0
changelog: 新建task
type: task
phase: postfix
description: 后处理（机械修正）
system_prompt: agent.md
defaults: {"reasoning_effort": "low", "temperature": 0.3}
---

<task>
对章节进行机械后处理，不调用LLM。

**触发方式：**「后处理」「修正格式」「清理章节」
</task>

<process>
## 后处理流程

1. **去标题 # 号**
   - 如果标题行以 `# ` 开头，去掉 `#`

2. **过滤源文标题**
   - 如果标题行与源文标题相同，替换为 `第{N}章`

3. **删重复标题行**
   - 如果第3行也是标题行，删除

4. **删末尾字数行**
   - 如果末尾是 `【字数：XXX字】`，删除

5. **XML格式提取**
   - 如果内容包含 `<chapter>` 标签，提取 `<content>` 中的内容

6. **检查空行**
   - 确保段落之间有空行
</process>

<output>
## 输出格式

直接修改原文件，不输出新内容。
</output>
