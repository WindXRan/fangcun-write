# AI网文小说项目 — 仿写引擎

## 项目定位

**独立项目**，基于自研仿写流程引擎，不依赖上游 oh-story-claudecode。

## 架构

```
test-rewrite（流程引擎 v3）
├── 三轮并行 Agent（风格分析→章纲→写章）
├── Lv1/Lv2/Lv3 防洗稿
├── 字数校验 + 超限重写
└── 章纲即真相
```

## Skill 路由表

| 命令 | Skill | 说明 |
|------|-------|------|
| `/story-rewrite`、`/仿写` | test-rewrite | 仿写流程引擎 |
| `/仿写vPlan`、`/vPlan` | story-rewrite_vPlan | 全书规划先行仿写引擎 |
| `/story-scan`、`/番茄扫描` | story-scan | 番茄小说排行榜分析 |
| `/story-cover`、`/封面` | story-cover | 小说封面生成 |
| `/story-compare`、`/对比` | story-compare | 仿写书与源文逐章对比 |
| `/novel-download`、`/下载小说` | novel-download | 番茄小说下载 |

## 文件结构

```
AI网文小说项目/
├── .claude/
│   ├── skills/                  # 所有 skill
│   │   ├── test-rewrite/        # 仿写流程引擎 v3（含 prompts/ tools/）
│   │   ├── story-rewrite_vPlan/ # 全书规划先行仿写引擎（含 prompts/ tools/）
│   │   ├── story-compare/       # 对比文件生成
│   │   ├── story-scan/          # 番茄排行榜分析
│   │   ├── story-cover/         # 封面生成
│   │   ├── novel-download/      # 小说下载
│   │   └── story-author-query/  # 作者查询
│   └── hooks/                   # 会话管理 hooks
├── novel-download-authors/      # 源文缓存（作者/书名，按章拆分）
└── {书名}/                      # 仿写产出
    ├── 正文/
    ├── 设定/
    ├── 大纲/
    ├── 真相文件/
    ├── 对比/
    └── 追踪/
```

## 运行模式

触发 /story-rewrite、/仿写 时，**全权代理**，自动执行以下决策无需问用户：
- 新书名：分析源文后自动给出候选并选定
- 仿写方向：自动判断
- 仿写体量：全集仿写

## 仿写项目识别

用户说"继续""续写"时，自动检测 `仿写框架.md`：
- 存在 → 仿写项目，路由到 test-rewrite
- 不存在 → 常规项目

## Compact 后恢复

写作中的关键上下文：
1. 当前写作项目名称和进度
2. 最近讨论的角色设定变更
3. 未完成的伏笔列表
4. 当前章节的情绪/节奏目标

如果存在 `{书名}/追踪/上下文.md`，compact 后首先读取恢复。
