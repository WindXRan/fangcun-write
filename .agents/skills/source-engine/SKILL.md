---
name: source-engine
version: 1.0.0
description: |
  源书级分析引擎。从小说原文提取事件表、生成故事骨架、制定改编策略。
  产物存放在 _cache/，供 story-engine 和 drama-engine 共用。
  触发方式：/source-engine、/源书分析、「提取事件」「生成骨架」「制定改编策略」
---

# source-engine：源书级分析引擎

从小说原文提取结构化产物，供下游引擎共用。

## 产物

| 产物 | 文件 | 说明 |
|------|------|------|
| 事件表 | `_cache/events.json` | 每章一行（角色/事件/主线关系/情绪/信息密度） |
| 故事骨架 | `_cache/story_skeleton.md` | 三幕结构/分集/付费卡点/股价级反转 |
| 改编策略 | `_cache/adaptation_strategy.md` | 核心改编原则/删减决策/世界观呈现 |
| 文笔指纹 | `_cache/styles/style_{N}.md` | 逐章风格分析（算法锚点 + LLM 分析） |

## 用法

```bash
# 完整流程（事件→骨架→改编）
python .agents/skills/source-engine/tools/pipeline.py --config configs/xxx.json

# 分步执行
python .agents/skills/source-engine/tools/pipeline.py --config configs/xxx.json --phase event
python .agents/skills/source-engine/tools/pipeline.py --config configs/xxx.json --phase skeleton
python .agents/skills/source-engine/tools/pipeline.py --config configs/xxx.json --phase adaptation
```

## 下游引擎

- **story-engine**：读取 events/skeleton/adaptation 注入 write-chapter prompt
- **drama-engine**：读取 events/skeleton/adaptation 作为剧本规划输入

## 配置文件

```json
{
  "base_dir": ".",
  "author": "作者名",
  "source_book": "源书名",
  "api_key": null,
  "model": "mimo-v2.5-pro",
  "model_overrides": {
    "event": "deepseek-chat"
  }
}
```

## 文件结构

```
source-engine/
├── SKILL.md
├── prompts/
│   ├── event_extraction.md    # 事件提取 prompt
│   ├── skeleton.md            # 故事骨架 prompt
│   └── adaptation.md          # 改编策略 prompt
└── tools/
    ├── file_io.py             # 源书级 I/O（_cache/ 读写）
    ├── source_analysis.py     # 生成逻辑（events/skeleton/adaptation）
    └── pipeline.py            # CLI 入口
```
