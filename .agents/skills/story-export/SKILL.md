# Skill: story-export

# story-export · 小说导出

将仿写章节合并导出为番茄小说格式的txt文件。

## 触发条件

用户说：`/export`、`导出小说`、`导出txt`、`合并导出`

## 输出格式

```
书名：XXX
状态：完结
字数：XXX
章节：XXX
分类：XXX（从concept.md提取）
标签：XXX（从源文提取）

简介：（从concept.md提取版本A）
XXX

========================================

第1章 XXX
...
```

## 使用方式

### 自动模式（推荐）

直接运行，自动查找项目目录：

```powershell
python .agents/skills/story-export/export.py <项目目录>
```

示例：
```powershell
python .agents/skills/story-export/export.py "projects/闻栖/分手了？秦少火速领证上位/rewrites/分手了？秦少火速领证上位仿写"
```

### 参数说明

| 参数 | 说明 | 必填 |
|------|------|------|
| 项目目录 | rewrites下的项目目录（包含chapters/和concept.md） | 是 |
| --output | 指定输出文件路径 | 否 |
| --encoding | 输出编码，默认utf-8 | 否 |

## 信息来源

| 字段 | 来源 |
|------|------|
| 书名 | concept.md的`# 《书名》`标题 |
| 分类 | concept.md的`**题材**`字段 |
| 标签 | 源文txt文件的`标签：`字段 |
| 简介 | concept.md的`版本A`简介 |
| 字数/章节 | 自动统计 |

## 文件结构

```
projects/{作者}/{源书}/
├── _cache/
│   └── {源书}.txt        # 源文（提取标签）
└── rewrites/{新书}/
    ├── concept.md         # 设定（提取书名/简介/题材）
    ├── chapters/          # 章节文件
    │   ├── ch_001.txt
    │   └── ...
    └── export/            # 导出目录（自动创建）
        └── {新书}.txt     # 导出文件
```
