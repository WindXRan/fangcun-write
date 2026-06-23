---
name: story-setup
version: 1.2.3
description: |
  网文写作工具集基础设施部署。将 hooks/rules/agents/CLAUDE.md 等基础设施部署到用户项目目录。
  触发方式：/story-setup、「准备写书」「帮我搭一下环境」「配置写作项目」
---

# story-setup：网文写作工具集基础设施部署

你是写作基础设施部署器。将网文写作工具集的全套基础设施部署到用户项目目录。

**执行铁律：不覆盖用户已有配置，合并而非替换。**

---

## Phase 1：检测项目状态

1. 检查当前目录是否已部署过（存在 `.story-deployed`）
2. 检查是否有书名目录
3. 检查 `.claude/settings.local.json` 是否存在
4. 检查 `.active-book` 文件是否存在
5. 检查 `opencode.json` 或 `.opencode/` 是否存在

## Phase 2：部署基础设施

### 部署清单

| Source | Target | 说明 |
|--------|--------|------|
| CLAUDE.md.tmpl | CLAUDE.md | 项目根配置 |
| hooks/ | .claude/hooks/ | 7 个 hook 脚本 |
| rules/*.md | .claude/rules/*.md | 4 条规则 |
| agents/*.md | .claude/agents/*.md | 7 个 agent |
| agent-references/ | .claude/skills/story-setup/references/ | 参考资料 |
| settings-hooks.json | .claude/settings.local.json | hooks 注册 |

### 2.1 部署 CLAUDE.md

- 读取模板，替换占位符
- 写入项目根目录（如已存在，按 marker/section 合并）

### 2.2 部署 Hooks

- 递归复制完整目录树到 `.claude/hooks/`
- 设置执行权限

### 2.3 部署 Rules

- 复制到 `.claude/rules/` 目录

### 2.4 部署 Agents

- 复制到 `.claude/agents/` 目录
- **部署后必须新开会话**

### 2.5 部署 Session State 模板

- 创建缺失的 `{书名}/追踪/上下文.md`

### 2.6 合并 Hooks 注册到 settings.local.json

### 2.7 创建部署标记

- 创建 `.story-deployed` 文件

## Phase 3：验证安装

1. 验证 hooks 注册
2. 验证 rules 路径
3. 验证 agents
4. 验证部署标记
5. 输出安装报告

---

## 模板占位符

| 占位符 | 替换规则 |
|--------|----------|
| `{项目名}` | 用户项目名称或目录名 |
| `{书名}` | 书名目录名 |
| `{目标平台}` | 目标发布平台 |
| `{作者名}` | 用户笔名或昵称 |

---

## 7 个专业 Agent

| Agent | 职责 |
|-------|------|
| story-architect | 故事架构 · 题材定位、大纲结构 |
| character-designer | 角色设计 · 角色档案、语言风格 |
| narrative-writer | 叙事写手 · 正文写作、去AI味 |
| consistency-checker | 一致性检查 · 事实冲突扫描 |
| story-researcher | 资料研究 · CDP 搜索+正文提取 |
| story-explorer | 故事查询 · 角色/伏笔/设定只读查询 |
| chapter-extractor | 章节提取 · 摘要+情节点+角色提及 |

---

## 7 个自动 Hook

| Hook | 触发时机 | 功能 |
|------|----------|------|
| session-start.sh | 会话开始 | 显示分支、进度快照 |
| session-end.sh | 会话结束 | 记录会话日志 |
| detect-story-gaps.sh | 会话开始 | 检测设定缺口 |
| pre-compact.sh | 上下文压缩前 | 保存进度快照 |
| post-compact.sh | 上下文压缩后 | 提示恢复上下文 |
| validate-story-commit.sh | git commit | 检查硬编码属性 |
| guard-outline-before-prose.sh | 写正文前 | 强制先搭大纲 |
