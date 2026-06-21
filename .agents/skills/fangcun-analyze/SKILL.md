---
name: fangcun-analyze
description: |
  源书级分析引擎。提取事件表、生成故事骨架、制定改编策略。产物供 fangcun-novel 和 fangcun-drama 共用。
  触发方式：「提取事件」「生成骨架」「分析这本书」「源书分析」
---

# fangcun-analyze：源书级分析引擎

## 你是 agent，负责：

1. **理解用户意图**（"分析这本书" → 跑全流程；"重新提取事件" → 只跑 event）
2. **读取源文和 prompt**
3. **派生子 agent 执行分析任务**
4. **检查输出质量**

## 产物（存放在 _cache/，两套引擎共用）

| 文件 | 说明 |
|------|------|
| `events.json` | 事件表（每章一行：角色/事件/主线关系/情绪） |
| `story_skeleton.md` | 故事骨架（三幕/分集/付费卡点/反转） |
| `adaptation_strategy.md` | 改编策略（8大要点/删减决策/世界观） |

## 目录结构

```
projects/{author}/{source_book}/
├── _cache/
│   ├── chapters/           # 源文章节（已拆章）
│   │   ├── 第1章.txt
│   │   └── ...
│   ├── events.json         # 事件表
│   ├── story_skeleton.md   # 故事骨架
│   └── adaptation_strategy.md  # 改编策略
```

## 流程

### Phase 1: 事件提取

**任务**：读取源文章节，提取每章的结构化事件信息。

**步骤**：
1. 读取 `_cache/chapters/` 目录，获取章节目录
2. 读取 `prompts/event_extraction.md`，获取提取规则
3. 派生子 agent（每批 5-10 章），子 agent 任务：
   - 读取章节文件
   - 按 prompt 格式输出事件行（一行，`|` 分隔 7 个字段）
   - 返回事件行
4. 收集所有事件行，写入 `_cache/events.json`

**事件格式**：
```json
[
  {"id": 1, "chapter_index": 1, "chapter": "第1章 标题", "event": "| 第1章 标题 | 角色 | 事件 | 关系 | 密度 | 时长 | 情绪 |"}
]
```

### Phase 2: 故事骨架

**任务**：基于事件表，生成故事骨架。

**步骤**：
1. 读取 `_cache/events.json`
2. 读取 `prompts/skeleton.md`
3. 派生子 agent，任务：
   - 分析事件表，提取故事核、人物小传、三幕结构
   - 按 prompt 格式输出 story_skeleton.md
   - 返回结果
4. 写入 `_cache/story_skeleton.md`

### Phase 3: 改编策略

**任务**：基于事件表和故事骨架，生成改编策略。

**步骤**：
1. 读取 `_cache/events.json`
2. 读取 `_cache/story_skeleton.md`
3. 读取 `prompts/adaptation.md`
4. 派生子 agent，任务：
   - 分析事件表和骨架，制定改编策略
   - 按 prompt 格式输出 adaptation_strategy.md
   - 返回结果
5. 写入 `_cache/adaptation_strategy.md`

## 配置

用户需要提供：
- `author`：作者名
- `source_book`：源书名
- `base_dir`：项目根目录（默认 "."）

## 质量检查

跑完后 agent 应该：
1. 读 `_cache/events.json`，检查有效事件数是否等于总章数
2. 读 `_cache/story_skeleton.md`，检查分集数是否合理
3. 如有失败章节，建议重跑

## 常见场景

| 用户说 | agent 做 |
|--------|----------|
| "分析这本书" | 跑全流程（event → skeleton → adaptation） |
| "重新提取事件" | 只跑 event |
| "骨架有问题" | 重新跑 skeleton |
| "看看分析结果" | 读 events.json + story_skeleton.md，汇报 |
