---
name: compare
version: 1.1.0
changelog: 添加trigger字段
type: task
phase: compare
description: 对比分析
trigger: "/compare", "/对比", "对比分析", "看看仿写质量"
system_prompt: agent.md
defaults: {"reasoning_effort": "low", "temperature": 0.3}
---

<task>
对比源文和仿写，生成对比报告。

**触发方式：**「对比」「对比分析」「看看仿写质量」
</task>

<process>
## 对比流程

1. **读取源文**
   - 读取源文章节内容

2. **读取仿写**
   - 读取仿写章节内容

3. **对比分析**
   - 情节走向对比
   - 角色设定对比
   - 冲突类型对比
   - 情绪基调对比
   - 风格对比

4. **生成报告**
   - 差异分析
   - 抄袭风险评估
   - 改进建议
</process>

<output>
## 输出格式

```
# 对比报告

## 章节 {N}

### 差异分析
- 情节走向：{对比结果}
- 角色设定：{对比结果}
- 冲突类型：{对比结果}
- 情绪基调：{对比结果}

### 抄袭风险评估
- 风险等级：{低/中/高}
- 风险点：{具体风险}

### 改进建议
- {建议1}
- {建议2}
```
</output>
