---
name: story-compare
description: |
  快速生成仿写书与源文的逐章对比文件，用于投稿前质量评估或问AI哪本更好。
trigger:
  - /story-compare、/对比
---

# story-compare：仿写对比文件生成

通过脚本生成 `{书名}/对比/对比_{start}-{end}.md`，无 AI 参与，纯数据对比 + 全文对照。

## 用法

```
/story-compare {书名}                  # 默认黄金三章（第1-3章）
/story-compare {书名} 1 10             # 指定区间
```

## 执行

```bash
python .claude/skills/story-compare/compare.py "{书名}" [起始章] [结束章]
```

## 输出

生成 `{书名}/对比/对比_{start}-{end}.md`，结构：

1. **统计对比表**（所有章节汇总，一目了然）
2. **版本A（源文）**（全部章节连着放，方便连续阅读）
3. **版本B（新书）**（全部章节连着放，方便连续阅读）

## 注意事项

1. 默认只比黄金三章，如需全书加 `1 9999`
2. 源文自动从 `novel-download-authors/` 查找
3. 只对比有正文的章节
