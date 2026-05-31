---
name: story-style
description: |
  写作风格/文风合集。存放女娲蒸馏出的作家文风Skill，供 story-rewrite 以 --style 参数加载。
  每个子目录是一个独立文风，含完整的SKILL.md和参考资料。
  路由规则：用户说「用XX风格写」「仿XX」「XX的文风」→ 加载对应文风 → 路由到 story-rewrite
  当前文风：wenqi（闻栖 · 番茄女频 · 穿书甜宠）
  自动化：女娲（huashu-nuwa）蒸馏网文作者时自动输出到此目录 + 创建 story-rewrite 插件
---

# story-style：写作风格/文风库

> 存放由女娲（huashu-nuwa）蒸馏出的作家文风Skill，供 story-rewrite 以 `--style` 参数加载。

## 是什么

`story-style` 是一个风格转发层，位于 `story-*` 工具链下。每个子目录是一个完整的作家文风：

```
skills/story-style/
├── SKILL.md           # 本转发层
└── {name}/            # 文风目录
    ├── SKILL.md       # 女娲蒸馏出的人物文风（内嵌 name: wenqi-perspective）
    └── references/    # 调研资料
```

## 文风列表

| 文风 | 目录 | 描述 | 体裁 | status |
|------|------|------|------|--------|
| 闻栖 | `wenqi/` | 女频·穿书甜宠·反套路偏爱·吐槽型女主 | 现代言情/古代言情/穿书/重生 | ✅ 可用 |

## 使用方式

```
# 路由到 story-rewrite，加载闻栖风格写全书
/story-rewrite --style=wenqi

# 路由到 story-rewrite-preview，试水3章
/story-rewrite-preview --style=wenqi
```

## 文风目录规范

每个文风目录必须包含：

| 文件 | 必须 | 说明 |
|------|------|------|
| `SKILL.md` | ✅ | 女娲蒸馏输出，含 frontmatter + 写作模型 + 表达DNA + 模板 + 质量检查清单 |
| `references/` | ✅ | 女娲调研的原始资料 |

`SKILL.md` 的 sections 结构决定了 story-rewrite 能从它提取到什么：

| section | 用途 |
|---------|------|
| frontmatter.trigger | 路由匹配词 + 风格插件兼容体裁 |
| `## 表达DNA` | → 替换「你的声音」（句式/高频词/对话风格） |
| `## 核心写作心智模型` + `## 决策启发式` + `## 价值观与反模式` | → 追加「写作原则」 |
| `## 质量检查清单` | → 审查标准 |
| `## 可运行的写作模板` | → 章纲结构参考 |

## story-rewrite 加载路径

`story-rewrite/styles/{name}/meta.json` 的 `source_skill` 指向 `skills/story-style/{name}/SKILL.md`。
