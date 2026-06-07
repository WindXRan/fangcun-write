# AI网文小说项目 — 仿写引擎

## 项目定位

**独立项目**，基于自研仿写流程引擎，不依赖上游 oh-story-claudecode。

## 架构

```
story-engine（guide模式）
├── Phase 1：一键pipeline（拆章+风格分析+创建目录）
├── Phase 2：开书（新书设定 + 全书弧线）
├── Phase 3：Guide生成（1 agent，20个文件）
├── Phase 4：写章（10 agents×N批，guide驱动，一次出稿）
└── Phase 5：批后（分层Critic + 冲突检测 + 分布一致性）
```

## Skill 路由表

| 命令 | Skill | 说明 |
|------|-------|------|
| `/仿写`、`/vPlan` | story-engine | 仿写引擎（guide模式） |
| `/分析风格` | story-style | 源文分析（插件式：style+hook+...） |
| `/story-scan`、`/番茄扫描` | story-scan | 番茄小说排行榜分析 |
| `/story-cover`、`/封面` | story-cover | 小说封面生成 |
| `/story-compare`、`/对比` | story-compare | 仿写书与源文逐章对比 |
| `/novel-download`、`/下载小说` | novel-download | 番茄小说下载 |

## 文件结构

```
AI网文小说项目/
├── .agents/
│   ├── skills/
│   │   ├── story-engine/             # 仿写引擎（主入口）
│   │   ├── story-style/              # 源文分析
│   │   ├── story-compare/            # 对比文件生成
│   │   ├── story-scan/               # 番茄排行榜分析
│   │   ├── story-cover/              # 封面生成
│   │   ├── novel-download/           # 小说下载
│   │   ├── story-author-query/       # 作者查询
│   │   └── _archived/                # 归档旧版 skill
│   └── hooks/
├── novel-download-authors/           # 源文 + 仿写（同一目录）
│   └── {作者名}/{书名}/
│       ├── 源文/                     # 拆章后章节
│       ├── 蒸馏/mode-b/             # 风格分析缓存
│       └── 仿写/{新书名}_仿写/
│           ├── 设定/
│           │   ├── 新书设定.md
│           │   ├── 全书弧线.md
│           │   └── guides/
│           │       ├── plot_guide_N.md
│           │       └── style_guide_N.md
│           ├── 追踪/
│           │   └── 真相.md
│           └── 正文/第N章.txt
```

## 运行模式

触发 `/仿写` 或 `/vPlan` 时，**全权代理**，自动执行以下决策无需问用户：
- 新书名：分析源文后自动给出候选并选定
- 仿写方向：自动判断
- 仿写体量：全集仿写

## 仿写项目识别

用户说"继续""续写"时，检测项目目录下是否有设定和大纲文件：
- 存在 → 仿写项目，路由到 vPlan 续写
- 不存在 → 新项目，从 Phase 1 开始

## Compact 后恢复

写作中的关键上下文：
1. 当前写作项目名称和进度
2. 最近讨论的角色设定变更
3. 未完成的伏笔列表
4. 当前章节的情绪/节奏目标

如果存在 `{书名}/追踪/上下文.md`，compact 后首先读取恢复。
