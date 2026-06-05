# AI网文小说项目 — 仿写引擎

基于自研仿写流程引擎的网文创作工具集。

## 核心功能

| 命令 | 说明 |
|------|------|
| `/story-rewrite` | 结构仿写 · 套用爆款骨架写新书 |
| `/story-rewrite-preview` | 仿写试水 · 只写3章预览效果 |
| `/story-review` | 一致性审查 · 多视角审稿 |
| `/story-cover` | 封面生成 · 书名题材分析 + AI出图 |
| `/story-style` | 写作风格知识库 |

## 快速开始

```
/story-rewrite --style=wenqi    # 用闻栖风格仿写
/story-rewrite-preview          # 先试写3章看看效果
/story-review                   # 审查一致性问题
/story-cover                    # 生成封面图
```

## 项目结构

```
.agents/skills/
├── story-rewrite/        # 仿写流程引擎
├── story-style/          # 写作风格知识库
│   └── wenqi/            # 闻栖风格
├── story/                # 路由入口
├── story-review/         # 一致性审查
├── story-cover/          # 封面生成
├── story-rewrite-preview/ # 仿写试水
└── huashu-nuwa/          # 文风蒸馏工具
```

## 风格系统

通过 `--style` 参数选配写作风格：

```
/story-rewrite --style=wenqi    # 用闻栖风格
/story-style                    # 查看可用风格
```

风格来源：
1. story-style 内置风格（wenqi 等）
2. huashu-nuwa 蒸馏的作者风格

## License

[MIT](./LICENSE)
