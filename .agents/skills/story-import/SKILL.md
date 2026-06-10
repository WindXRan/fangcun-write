---
name: story-import
description: |
  标准化导入工具。替代手动拆章，自动完成：
  1. 解析原始txt（书名、作者、简介、章节）
  2. 拆章到 chapters/ 目录
  3. 生成 _header.txt 和 _toc.txt
  触发方式：/story-import、/导入小说、「导入这本书」「帮我导入」
---

# story-import · 标准化导入

## 功能

- 自动解析原始txt文件的书籍信息（书名、作者、简介等）
- 自动按"第X章"拆分章节
- 生成标准的 `_header.txt` 和 `_toc.txt`
- 输出到 `projects/{作者}/{书名}/_cache/` 目录

## 使用

```bash
# 基本用法
python tools/story_import.py <txt文件路径>

# 指定输出目录
python tools/story_import.py <txt文件路径> --output <输出目录>
```

## 示例

```bash
# 导入下载的小说
python tools/story_import.py "projects/闻栖/将门有朵病娇花/将门有朵病娇花.txt"

# 指定输出目录
python tools/story_import.py "downloads/春深锁惊鸿.txt" --output "projects/暴躁123/春深锁惊鸿/_cache"
```

## 输出结构

```
projects/{作者}/{书名}/
└── _cache/
    ├── _header.txt          # 书籍信息
    ├── _toc.txt             # 目录
    └── chapters/
        ├── 第1章.txt
        ├── 第2章.txt
        └── ...
```

## 支持的格式

- 番茄小说下载的txt格式
- 标准的"第X章"章节格式
- UTF-8 或 GBK 编码

## 注意事项

- 如果无法解析书名，会使用文件名作为书名
- 章节必须以"第X章"开头才能被识别
- 简介会自动截取到第一个"==="或"【第"之前
