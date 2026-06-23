---
name: story-io
description: |
  小说导入/导出工具。导入：txt拆章。导出：章节合并。
  触发方式：/导入、/导出、/story-import、/story-export
---

# story-io · 小说导入/导出

## 导入

读取 txt 源文件，自动识别书名、作者、章节、番外，输出到标准目录。

```
/导入 <txt文件路径>
```

### 步骤
1. 读取前 2000 字，识别书名、作者、简介
2. 全文识别章节和番外
3. 拆分到 chapters/ 和 fanwai/
4. 生成 _header.txt 和 _toc.txt

### 输出结构
```
projects/{作者}/{书名}/_cache/
├── _header.txt
├── _toc.txt
├── chapters/第001章.txt
└── fanwai/番外1.txt
```

## 导出

合并章节为完整小说，格式与导入格式一致。

```
/导出 <项目目录>
```

### 步骤
1. 读取 chapters/ 和 fanwai/
2. 读取 _header.txt
3. 合并为完整 txt
4. 输出到 export/ 目录
