---
version: 1
type: user
phase: analyze
description: 分析原著结构，生成集数规划
required_vars: ["novel_summary", "total_chars", "episodes", "minutes_per_episode"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-pro", "max_tokens": 4096, "reasoning_effort": "high", "temperature": 0.3}
---

你是资深短剧编剧。分析以下原著，规划短剧结构。

## 原著信息
- 总字数：{total_chars}字
- 目标集数：{episodes}集
- 每集时长：{minutes_per_episode}分钟
- 每集平均字数：{avg_chars}字

## 原著摘要
{novel_summary}

## 任务

1. **主线提取**：提取核心主线（3-5句话）
2. **高潮点标注**：标注10-15个关键高潮点（适合做集尾悬念）
3. **集数规划**：每集的起止章节、核心事件、悬念钩子
4. **节奏控制**：
   - 第1集：强钩子，必须抓人
   - 每3-5集一个小高潮
   - 每10集一个大转折
   - 结尾集：收束所有伏笔

## 输出格式

```json
{
  "主线": "核心剧情线",
  "高潮点": [
    {"集数": 1, "事件": "xxx", "类型": "悬念/反转/情感"},
    ...
  ],
  "集数规划": [
    {"集": 1, "章节": "1-3", "核心事件": "xxx", "悬念": "xxx"},
    ...
  ]
}
```
