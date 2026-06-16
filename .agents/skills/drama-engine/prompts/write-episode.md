---
version: 1
type: user
phase: write-episode
description: 将单章改编为1分钟短剧剧本
required_vars: ["chapter_text", "episode_num", "target_chars", "novel_name"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-pro", "max_tokens": 2048, "reasoning_effort": "high", "temperature": 0.6}
---

你是红果短剧编剧。将以下章节改编为1分钟短剧剧本。

## 要求

- **时长**：1分钟（约{target_chars}字）
- **节奏**：前5秒必须有钩子，最后5秒必须有悬念
- **格式**：红果短剧标准格式
- **风格**：快节奏、强冲突、情绪饱满

## 红果短剧格式

```
第{episode_num}集 标题

场景：外景/内景 - 地点 - 时间

[角色名]（动作/表情）
对白。

[画面描述]
视觉描述。
```

## 改编规则

1. **删减**：删除描写性文字，保留对话和动作
2. **冲突**：每集必须有一个核心冲突
3. **悬念**：结尾必须留钩子（反转/揭秘/危机）
4. **对话**：口语化，短句，有情绪张力
5. **画面**：用[画面描述]标注关键视觉镜头

## 原文章节

{chapter_text}

## 输出

直接输出剧本，不要加任何分析或说明。
