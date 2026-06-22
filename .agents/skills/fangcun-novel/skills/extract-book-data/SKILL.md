---
name: extract-book-data
version: 1.0.0
description: |
  提取书籍数据。从设定文件中提取结构化数据，输出 book_data.json。
  触发方式：「提取数据」「提取设定」「生成book_data」
metadata:
  author: fangcun-team
---

# 提取书籍数据

你是数据提取助手，负责从设定文件中提取结构化数据。

**核心职责：**
- 读取设定文件（concept.md、characters.md、world.md、plot.md、book_info.md）
- 提取结构化数据
- 输出 book_data.json

---

## 流程总览

| 步骤 | 任务 | 产出 |
|------|------|------|
| 1 | 读取设定文件 | 原始数据 |
| 2 | 提取结构化数据 | 结构化数据 |
| 3 | 输出 book_data.json | 最终产物 |

---

## Step 1：读取设定文件

**任务：** 读取所有设定文件。

**读取文件：**
- `rewrites/{book_name}/concept.md`
- `rewrites/{book_name}/characters.md`
- `rewrites/{book_name}/world.md`
- `rewrites/{book_name}/plot.md`
- `rewrites/{book_name}/book_info.md`

---

## Step 2：提取结构化数据

**任务：** 从设定文件中提取结构化数据。

**提取内容：**
1. **书名**：从 book_info.md 提取
2. **作者**：从配置文件提取
3. **题材**：从 concept.md 提取
4. **风格类型**：从 concept.md 提取
5. **角色列表**：从 characters.md 提取
6. **世界观**：从 world.md 提取
7. **剧情设定**：从 plot.md 提取

---

## Step 3：输出 book_data.json

**任务：** 将提取的数据输出为 JSON 格式。

**输出格式：**
```json
{
  "book_name": "书名",
  "author": "作者",
  "source_book": "源书名",
  "genre": "题材",
  "style_type": "风格类型",
  "characters": [
    {
      "name": "角色名",
      "source_name": "源文名",
      "gender": "性别",
      "role": "功能位",
      "personality": "性格内核"
    }
  ],
  "world": {
    "time_period": "时代背景",
    "geography": "地理设定",
    "social_structure": "社会结构"
  },
  "plot": {
    "main_line": "主线概述",
    "emotional_core": "情感内核",
    "conflict": "核心冲突"
  }
}
```

---

## 使用方式

```bash
# 提取数据
/extract-book-data

# 或
/提取数据
```

---

## 输出路径

```
rewrites/{book_name}/book_data.json
```
