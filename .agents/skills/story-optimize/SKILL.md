# Skill: story-optimize

# story-optimize：审稿→沉淀→修复

通用的 AI 痕迹检测和修复 skill，每本书写完后自动运行。

## 流程

```
分批审稿（N 并行） → 汇总问题 → 批量修复
```

### 1. 分批审稿
- 每批 5-10 章，LLM 分析 AI 痕迹和结构问题
- 输出 JSON 问题清单（type/category/severity/fix）

### 2. 汇总问题
- 合并所有批次，去重，按严重程度排序
- 统计问题频率，生成修复指令

### 3. 批量修复
- 按问题清单逐章修复
- 只改有问题的地方，保持字数±10%

## 检查维度

| 维度 | 检查项 | 严重程度 |
|------|--------|----------|
| AI痕迹 | 感官堆叠、情绪公式、对话节奏单一、章尾公式、内心三连问 | high |
| 结构 | 信息密度、时间线、人设矛盾、配角功能 | medium |
| 文笔 | 比喻陈词滥调、重复环境描写、节奏拖沓 | low |

## 用法

```bash
# 独立运行
python .agents/skills/story-optimize/optimize.py --config configs/xxx.json --start 1 --end 10

# Pipeline 集成（Phase 3.9）
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase optimize

# 只审不修
python .agents/skills/story-optimize/optimize.py --config configs/xxx.json --dry-run
```

## 输出

```
rewrites/{书名}/optimize/
├── batch_{start}_{end}.json    # 每批审稿结果
├── summary.json                # 汇总问题清单
└── fix_log.json                # 修复日志
```

## Prompt 文件

| 文件 | 用途 |
|------|------|
| `prompts/analyze_batch.md` | 分批审稿 |
| `prompts/summarize.md` | 汇总问题 |
| `prompts/fix_chapter.md` | 修复单章 |
