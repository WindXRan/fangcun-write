---
name: style-index
version: 1.0.0
description: |
  风格索引。管理所有作者的风格skill。
  触发方式：「查看风格索引」「有哪些作者风格」
---

# 风格索引

管理所有作者的风格skill。

## 使用方式

1. 查看索引：读取 `index.md`
2. 查找作者：在索引中查找作者名
3. 使用风格：读取对应的 style.md

## 索引文件

`index.md` 包含所有已蒸馏的作者风格。

## 子skill目录

```
.agents/skills/
├── style-index/              # 索引skill
│   ├── SKILL.md
│   └── index.md
├── style-{作者名}/           # 子skill
│   └── style.md
└── ...
```
