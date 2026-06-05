# AI网文小说项目 — 仿写引擎

## 项目定位

**独立项目**，基于自研仿写流程引擎，不依赖上游 oh-story-claudecode。

## 架构

```
story-rewrite_vPlan（全书规划先行引擎）
├── Phase 0：源文分析（可缓存，独立skill可并行）
│   ├── phase0-style：拆章+风格指纹+inkos 8维度
│   └── phase0-strategy：排除项+节奏骨架+叙事策略
├── Phase 1：全书规划（弧线骨架+章纲+映射）
└── Phase 2：纯写作出稿（10 agents并行，无后处理）
```

## Skill 路由表

| 命令 | Skill | 说明 |
|------|-------|------|
| `/仿写`、`/vPlan` | story-rewrite_vPlan | 仿写引擎（全书规划先行） |
| `/分析风格` | story-rewrite_phase0-style | 源文风格分析（可缓存） |
| `/分析策略` | story-rewrite_phase0-strategy | 源文叙事策略分析（可缓存） |
| `/story-scan`、`/番茄扫描` | story-scan | 番茄小说排行榜分析 |
| `/story-cover`、`/封面` | story-cover | 小说封面生成 |
| `/story-compare`、`/对比` | story-compare | 仿写书与源文逐章对比 |
| `/novel-download`、`/下载小说` | novel-download | 番茄小说下载 |

## 文件结构

```
AI网文小说项目/
├── .claude/
│   ├── skills/
│   │   ├── story-rewrite_vPlan/       # 仿写引擎（主入口）
│   │   ├── story-rewrite_phase0-style/     # 源文风格分析
│   │   ├── story-rewrite_phase0-strategy/  # 源文叙事策略分析
│   │   ├── story-compare/             # 对比文件生成
│   │   ├── story-scan/                # 番茄排行榜分析
│   │   ├── story-cover/               # 封面生成
│   │   ├── novel-download/            # 小说下载
│   │   ├── story-author-query/        # 作者查询
│   │   └── _archived/                 # 归档旧版 skill
│   └── hooks/
├── novel-download-authors/            # 源文缓存（只读）
│   └── {作者名}/{书名}/
│       ├── 源文/                      # 拆章后章节
│       └── 蒸馏/mode-b/              # 风格分析缓存
└── 仿写/                              # 所有仿写产出
    └── {新书名}/
        ├── 设定/
        ├── 大纲/
        └── 正文/
```

## 运行模式

触发 `/仿写` 或 `/vPlan` 时，**全权代理**，自动执行以下决策无需问用户：
- 新书名：分析源文后自动给出候选并选定
- 仿写方向：自动判断
- 仿写体量：全集仿写

## 仿写项目识别

用户说"继续""续写"时，检测项目目录下是否有设定和大纲文件：
- 存在 → 仿写项目，路由到 vPlan 续写
- 不存在 → 新项目，从 Phase 0 开始

## Compact 后恢复

写作中的关键上下文：
1. 当前写作项目名称和进度
2. 最近讨论的角色设定变更
3. 未完成的伏笔列表
4. 当前章节的情绪/节奏目标

如果存在 `{书名}/追踪/上下文.md`，compact 后首先读取恢复。
