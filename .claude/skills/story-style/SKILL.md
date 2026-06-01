---
name: story-style
description: |
  写作风格知识库 · 承载所有写作规则和风格定义。
  story-rewrite 通过 --style 参数调用，agent 直接读取本文件获取写作知识。
  触发方式：/story-style、/文风、「有什么风格」「风格列表」「用XX风格写」
---

# story-style：写作风格知识库

## 风格发现

| 位置 | 来源 |
|------|------|
| `.claude/skills/story-style/*/SKILL.md` | 网文作者文风 |
| `.claude/skills/*-perspective/SKILL.md` | 通用人物 Skill |

目录下存在 `SKILL.md` → 注册为可用风格。风格名 = 目录名。
