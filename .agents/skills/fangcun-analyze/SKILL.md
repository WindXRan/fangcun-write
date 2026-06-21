---
name: fangcun-analyze
description: |
  源书级分析引擎。提取事件表、生成故事骨架、制定改编策略。产物供 fangcun-novel 和 fangcun-drama 共用。
  触发方式：「提取事件」「生成骨架」「分析这本书」「源书分析」
---

# fangcun-analyze：源书级分析引擎

## 你是 agent，负责：

1. **理解用户意图**（"分析这本书" → 跑全流程；"重新提取事件" → 只跑 event）
2. **组装正确的命令**
3. **检查输出质量**
4. **处理错误**

## 产物（存放在 _cache/，两套引擎共用）

| 文件 | 说明 |
|------|------|
| `events.json` | 事件表（每章一行：角色/事件/主线关系/情绪） |
| `story_skeleton.md` | 故事骨架（三幕/分集/付费卡点/反转） |
| `adaptation_strategy.md` | 改编策略（8大要点/删减决策/世界观） |

## 流程（混合模式）

### Phase 1: 事件提取（Python，高效并行）

```bash
python .agents/skills/fangcun-analyze/tools/pipeline.py --config {config} --phase event
```

- 滑窗上下文（前2章摘要）
- 并行处理（默认5线程）
- 增量保存（已有跳过）
- 格式严格（一行 `|` 分隔 7 字段）

### Phase 2: 故事骨架（agent，可迭代优化）

agent 自己执行：
1. 读取 `_cache/events.json`
2. 读取 `prompts/skeleton.md`
3. 分析事件表，生成骨架
4. 写入 `_cache/story_skeleton.md`

### Phase 3: 改编策略（agent，可迭代优化）

agent 自己执行：
1. 读取 `_cache/events.json`
2. 读取 `_cache/story_skeleton.md`
3. 读取 `prompts/adaptation.md`
4. 生成改编策略
5. 写入 `_cache/adaptation_strategy.md`

## 配置文件

```json
{
  "base_dir": ".",
  "author": "作者名",
  "source_book": "源书名",
  "api_key": null,
  "api_base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat"
}
```

## 质量检查（agent 自动执行）

跑完后 agent 应该：
1. 读 `_cache/events.json`，检查有效事件数是否等于总章数
2. 读 `_cache/story_skeleton.md`，检查分集数是否合理
3. 如有失败章节，建议重跑

## 常见场景

| 用户说 | agent 做 |
|--------|----------|
| "分析这本书" | 跑全流程（event → skeleton → adaptation） |
| "重新提取事件" | 跑 --phase event（增量，已有跳过） |
| "骨架有问题" | 重新跑 skeleton（agent 模式） |
| "看看分析结果" | 读 events.json + story_skeleton.md，汇报 |
