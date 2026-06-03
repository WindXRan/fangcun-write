---
name: story-compare
description: |
  快速生成仿写书与源文的逐章对比文件，用于投稿前质量评估或问AI哪本更好。
trigger:
  - /story-compare、/对比
---

# story-compare：仿写对比文件生成

通过脚本生成 `{书名}/对比/{区间}_对比.md`，无 AI 参与，纯数据对比。

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

生成 `{书名}/对比/对比_{start}-{end}.md`，包含每章的统计对比：

| 维度 | 源文 | 新书 |
|------|------|------|
| 正文字数 | ... | ... |
| 段落数 | ... | ... |
| 句数 | ... | ... |
| 对话占比 | ... | ... |
| 平均句长(字) | ... | ... |

及开篇句对比。

## 注意事项

1. 默认只比黄金三章，如需全书加 `1 9999`
2. 源文自动从 `novel-download-authors/` 查找
3. 只对比有正文的章节
