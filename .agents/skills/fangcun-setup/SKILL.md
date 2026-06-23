---
name: fangcun-setup
version: 1.0.0
description: |
  方寸网文写作工具集基础设施部署。将 hooks/rules/agents/CLAUDE.md 等基础设施部署到用户项目目录。
  触发方式：/fangcun-setup、「准备写书」「帮我搭一下环境」「配置写作项目」
---

# fangcun-setup：方寸网文写作工具集基础设施部署

你是写作基础设施部署器。将方寸网文写作工具集的全套基础设施部署到用户项目目录。

**执行铁律：不覆盖用户已有配置，合并而非替换。**

---

## Phase 1：检测项目状态

1. 检查当前目录是否已部署过（存在 `.fangcun-deployed`）
2. 检查是否有书名目录（包含 `rewrites/` 或 `chapters/` 的目录）
3. 检查项目配置文件是否存在
4. 检查 `.active-book` 文件是否存在

## Phase 2：部署基础设施

### 部署清单

| 组件 | 说明 |
|------|------|
| CLAUDE.md | 项目根配置，包含 skill 路由表和协作规则 |
| hooks/ | 自动触发的 hook 脚本 |
| rules/ | 路径范围规则 |
| agents/ | 专业 agent 定义 |

### 2.1 部署 CLAUDE.md

创建或更新项目根目录的 CLAUDE.md，包含：

```markdown
# 方寸网文写作项目

## Skill 路由

| 命令 | 说明 |
|------|------|
| /fangcun | 路由入口 |
| /fangcun-write | 长篇写作/仿写 |
| /fangcun-analyze | 拆文分析 |
| /fangcun-review | 多视角审查 |
| /fangcun-deslop | 去AI味 |
| /fangcun-cover | 封面生成 |

## 文件结构

{书名}/
├── _cache/chapters/        # 源文章节缓存
├── rewrites/{新书名}/
│   ├── concept.md          # 设定+角色+弧线
│   ├── characters.md       # 角色名映射表
│   ├── guides/plot_{N}.md  # 章纲
│   ├── chapters/ch_{N}.txt # 正文
│   └── compare/            # 对比报告
└── .fangcun-deployed       # 部署标记
```

### 2.2 创建部署标记

创建 `.fangcun-deployed` 文件：

```yaml
deployed_at: <timestamp>
version: 1.0.0
skills:
  - fangcun
  - fangcun-write
  - fangcun-analyze
  - fangcun-review
  - fangcun-deslop
  - fangcun-cover
```

## Phase 3：验证安装

1. 验证 CLAUDE.md 存在且包含路由表
2. 验证部署标记文件存在
3. 输出安装报告

---

## 流程衔接

| 时机 | 跳转到 | 命令 |
|---|---|---|
| 部署完成，开始写作 | fangcun-write | `/fangcun-write` |
| 导入已有小说 | story-import | `/story-import` |
| 需要浏览器登录态 | browser-cdp | `/browser-cdp` |
