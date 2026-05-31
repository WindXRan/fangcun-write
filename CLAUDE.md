# AI网文小说项目 — 网文写作工具集

## Skill 源目录

**`skills/` 是唯一源目录**，所有 skill 修改在 `skills/` 中进行。`.claude/skills/` 由 `/story-setup` 自动从 `skills/` 部署生成，不要手动编辑。

## Skill 路由表

| 命令 | Skill | 说明 |
|------|-------|------|
| `/story`、`/网文` | story | 工具箱路由 · 模糊意图自动分发 |
| `/story-setup`、`/准备写书` | story-setup | 环境部署 · hooks/rules/agents/CLAUDE.md 一键部署 |
| `/story-long-write`、`/写长篇` | story-long-write | 长篇网文写作（逐章推进） |
| `/story-short-write`、`/写短篇` | story-short-write | 短篇网文写作（情绪驱动） |
| `/story-long-analyze`、`/长篇拆文` | story-long-analyze | 长篇小说深度拆解 |
| `/story-short-analyze`、`/短篇拆文` | story-short-analyze | 短篇小说拆文分析 |
| `/story-long-scan`、`/长篇扫描` | story-long-scan | 长篇小说批量扫描 |
| `/story-short-scan`、`/短篇扫描` | story-short-scan | 短篇小说批量扫描 |
| `/story-deslop`、`/去AI味` | story-deslop | 去除 AI 写作痕迹 |
| `/story-import`、`/导入` | story-import | 逆向导入已有小说到项目结构 |
| `/story-review`、`/审查` | story-review | 多视角对抗式审查 |
| `/story-cover`、`/封面` | story-cover | 生成封面图 |
| `/story-publish`、`/发布`、`/番茄标签` | story-publish | 番茄小说发布 · 标签推荐 |
| `/story-export-docx`、`/导出` | story-export-docx | 正文导出 Word 文档 |
| `/story-rewrite`、`/仿写`、`/结构仿写` | story-rewrite | 结构仿写 · 直接写全书 |
| `/story-rewrite-preview`、`/仿写试水` | story-rewrite-preview | 仿写试水 · 只写3章预览 |
| `/story-synopsis`、`/简介` | story-synopsis | 小说简介生成 · 多版本对比（全局 skill） |
| `/browser-cdp` | browser-cdp | 浏览器 CDP 工具 |
| `/meta-iterate`、`/迭代`、`/自我迭代` | meta-iterative-improvement | 元迭代改进 - 让技能自我进化（全局 skill） |

---

## 文件结构

- `skills/` — **skill 源目录**（唯一修改点，`/story-setup` 自动同步到 `.claude/skills/`）
- `拆文库/` — 拆文分析结果存放目录
- `{书名}/正文/` — 长篇小说正文章节
- `{书名}/设定/` — 角色设定、世界设定
- `{书名}/大纲/` — 卷纲、细纲
- `{书名}/追踪/` — 上下文.md（写作上下文）、伏笔.md
- `{书名}/对标/` — 对标作品分析

---

## 协作规则

Agent 间的协调关系由各 Agent 定义文件的职责边界描述，不需要独立协调规则文件。

## Compact 后恢复上下文

此部分在 compact 后自动生效。CLAUDE.md 在每次 compact 后会被重新加载。
写作中的关键上下文：
1. 当前写作项目名称和进度
2. 最近讨论的角色设定变更
3. 未完成的伏笔列表
4. 当前章节的情绪/节奏目标

如果存在 {书名}/追踪/上下文.md，compact 后首先读取恢复上下文。
