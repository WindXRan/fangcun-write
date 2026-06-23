---
name: writing-knowledge
version: 1.0.0
description: |
  网文写作知识库管理。将各种多模态写作资料（理论、技巧、模板）导入知识库，供仿写/续写时参考。
  触发方式：/导入知识库、/写作资料、「导入理论」「整理写作资料」
metadata:
  author: fangcun-team
---

# writing-knowledge：网文写作知识库

## 定位

**写作资料的结构化存储，与 style-distill（作者风格）并行。**

| 维度 | style-distill | writing-knowledge |
|------|---------------|-------------------|
| 内容 | 作者风格（怎么写） | 写作理论（写什么） |
| 产出 | 赛博作者 agent | 结构化知识库 |
| 用途 | 模仿写作 | 参考决策 |

## 支持的输入格式

| 格式 | 处理方式 |
|------|----------|
| `.md` / `.txt` | 直接导入，按章节拆分 |
| `.pdf` | 提取文本（需 PyPDF2） |
| `.json` | 结构化数据直接导入 |
| 图片 | OCR 提取文字（需 pytesseract） |
| 目录 | 批量导入所有文件 |

## 知识库结构

```
knowledge/_writing/
├── theory/                    # 创作理论
│   ├── 核心总论.md
│   ├── 线纲体系.md
│   └── ...
├── techniques/                # 写作技巧
│   ├── 爽点设计.md
│   ├── 人物塑造.md
│   └── ...
├── templates/                 # 模板
│   ├── 大纲模板.md
│   ├── 拆书框架.md
│   └── ...
├── categories/                # 品类策略
│   ├── 都市.md
│   ├── 玄幻.md
│   └── ...
├── market/                    # 市场数据
│   ├── 爽文桥段.md
│   ├── 题材模板.md
│   └── ...
└── index.json                 # 索引
```

## 流程

```
Step 1: 识别输入（文件/目录/URL）
    ↓
Step 2: 检测格式，选择处理方式
    ↓
Step 3: 提取内容，清洗格式
    ↓
Step 4: 分类（理论/技巧/模板/品类/市场）
    ↓
Step 5: 拆分章节，生成索引
    ↓
Step 6: 写入 knowledge/_writing/
```

## 使用

```bash
# 导入单个文件
/导入知识库 网文创作理论体系·完整归总V2.md

# 导入目录
/导入知识库 ./写作资料/

# 导入并指定分类
/导入知识库 爽点设计.md --category techniques

# 查看知识库状态
/知识库状态
```

## 与其他 skill 的协作

- **style-distill**：作者风格（怎么写）→ 赛博作者
- **writing-knowledge**：写作理论（写什么）→ 知识库
- **fangcun-novel**：仿写时同时参考两者
