---
name: story-io
description: |
  小说导入/导出工具。导入：txt拆章。导出：章节合并。
trigger:
  - /story-io
  - /导入
  - /导出
  - /拆章
  - /合并章节
---

# story-io：小说导入/导出

## 导入（拆章）

将单个 .txt 文件拆分为独立章节文件，生成书籍元信息。

```bash
python .agents/skills/story-io/import_chapters.py "<输入文件>" [输出目录]
```

输出：
- `chapters/第N章.txt` — 逐章正文
- `_header.txt` — 书名/作者/分类/标签/简介
- `chapters/_toc.txt` — 章节目录

## 导出（合并）

将章节目录合并为单个 .txt 文件，输出格式与导入源文件一致。

```bash
python .agents/skills/story-io/export_chapters.py <章节目录> <输出文件>
```

## 用法

```
/导入 <txt文件路径>           # 拆章
/导出 <章节目录>              # 合并为 .txt
```
