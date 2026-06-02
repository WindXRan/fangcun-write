# AI网文小说项目 — 仿写引擎

## 项目定位

**独立项目**，基于自研仿写流程引擎，不依赖上游 oh-story-claudecode。

## 架构

```
story-rewrite（流程引擎）     story-style（知识库）
├── 调度 Agent               ├── 写作原则
├── 状态管理                 ├── 钩子类型
├── 质量校验                 ├── 角色设计
└── 进度追踪                 ├── 对话技法
                             ├── 去AI规则
                             ├── 禁用词
                             └── 质量检查
```

**职责分离**：rewrite = 调度器，style = 知识库

## Skill 路由表

| 命令 | Skill | 说明 |
|------|-------|------|
| `/story`、`/网文` | story | 工具箱路由 |
| `/story-rewrite`、`/仿写` | story-rewrite | 仿写流程引擎 |
| `/story-style`、`/文风` | story-style | 写作风格知识库 |
| `/story-review`、`/审查` | story-review | 一致性审查 |
| `/story-scan`、`/番茄扫描` | story-scan | 番茄小说排行榜分析 |
| `/story-distill`、`/蒸馏`、`/炼丹` | story-distill | 网文作者蒸馏（默认 write 模式，`--mode=review` 生成审稿框架） |

## 文件结构

```
AI网文小说项目/
├── .claude/
│   ├── skills/
│   │   ├── story-rewrite/      # 仿写流程引擎
│   │   ├── story-style/        # 写作风格知识库
│   │   │   ├── SKILL.md        # 通用写作知识
│   │   │   ├── references/     # 详细参考文件
│   │   │   └── wenqi/          # 闻栖风格
│   │   ├── story/              # 路由入口
│   │   ├── story-review/       # 一致性审查
│   │   ├── story-long-scan/    # 长篇网文扫榜
│   │   └── story-scan/         # 番茄小说排行榜分析
│   └── hooks/                  # 会话管理 hooks
├── .claude/skills/novel-download/novel-download-authors/  # 蒸馏的作者数据
└── {书名}/                     # 仿写产出
    ├── 正文/
    ├── 设定/
    ├── 大纲/
    └── 追踪/
```

## 仿写项目识别

用户说"继续""续写"时，自动检测 `仿写框架.md`：
- 存在 → 仿写项目，路由到 story-rewrite
- 不存在 → 常规项目

## 风格系统

通过 `--style` 参数选配写作风格：

```
/story-rewrite --style=wenqi    # 用闻栖风格
/story-style                    # 查看可用风格
```

风格来源：
1. story-style 内置风格（wenqi 等）
2. novel-download-authors/ 目录下的蒸馏数据（位于 .claude/skills/novel-download/）

## Compact 后恢复

写作中的关键上下文：
1. 当前写作项目名称和进度
2. 最近讨论的角色设定变更
3. 未完成的伏笔列表
4. 当前章节的情绪/节奏目标

如果存在 `{书名}/追踪/上下文.md`，compact 后首先读取恢复。
