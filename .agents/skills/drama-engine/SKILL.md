---
name: drama-engine
description: |
  小说转短剧剧本引擎。基于 Toonflow 原生 3 阶段 pipeline：故事骨架 → 改编策略 → 剧本编写。
  触发方式：「写剧本」「改编短剧」「小说转剧本」「帮我写剧本」
allowed-tools: Bash(python *)
---

# drama-engine：短剧剧本引擎

## 你是 agent，负责：

1. **理解用户意图**（"把这本书改成短剧" → 跑全流程）
2. **组装正确的命令**
3. **检查输出质量**（剧本格式、字数、角色名）
4. **处理错误**

## 流程

```
event → skeleton → skeleton_review → adaptation → adaptation_review → script → export
```

审核前置：骨架/策略产出后立即审核，不通过则修正后再进入下一阶段。

```bash
# 全流程
python .agents/skills/drama-engine/tools/pipeline.py --config {config}

# 分步执行
python .agents/skills/drama-engine/tools/pipeline.py --config {config} --phase event
python .agents/skills/drama-engine/tools/pipeline.py --config {config} --phase skeleton
python .agents/skills/drama-engine/tools/pipeline.py --config {config} --phase review --review-target skeleton
python .agents/skills/drama-engine/tools/pipeline.py --config {config} --phase adaptation
python .agents/skills/drama-engine/tools/pipeline.py --config {config} --phase review --review-target adaptation
python .agents/skills/drama-engine/tools/pipeline.py --config {config} --phase script --start 1 --end 10
python .agents/skills/drama-engine/tools/pipeline.py --config {config} --phase export

# 断点续传
python .agents/skills/drama-engine/tools/pipeline.py --config {config} --phase resume

# 查看进度
python .agents/skills/drama-engine/tools/pipeline.py --config {config} --phase status
```

## 配置文件

```json
{
  "novel_name": "原著书名",
  "drama_name": "剧本名",
  "source_dir": "projects/作者/书名/_cache/chapters",
  "output_dir": "projects/作者/书名/drama",
  "api_key": "sk-xxx",
  "api_base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "model_overrides": {
    "event": "deepseek-chat"
  },
  "project": {
    "episodes": 30,
    "episode_duration": 2,
    "chapter_range": [1, 153],
    "platform": "竖屏9:16",
    "style": "甜宠喜剧",
    "paywall": "前3集免费，第4集起付费"
  }
}
```

## 输出格式

剧本使用 `<scriptItem>` XML 标签包裹，△ 标记场景描述。

## 质量检查（agent 自动执行）

跑完后 agent 应该：
1. 读 `scripts/ep_001.txt`，检查格式是否正确（△标记、场景标题、台词）
2. 检查字数是否在 2000-3000
3. 检查角色名是否正确
4. 读 `reviews/` 目录，汇报审核评分
5. 如有问题，告诉用户

## 常见场景

| 用户说 | agent 做 |
|--------|----------|
| "把这本书改成短剧" | 配置参数 → 跑全流程 |
| "写前10集剧本" | 跑 --phase script --start 1 --end 10 |
| "继续写" | 跑 --phase resume |
| "看看剧本质量" | 读 scripts/ → 跑 --phase review |
| "骨架有问题" | 跑 --phase skeleton（覆盖旧的）→ 跑 --phase review |
