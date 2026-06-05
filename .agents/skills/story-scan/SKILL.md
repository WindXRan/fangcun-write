---
name: story-scan
version: 1.0.0
description: |
  番茄小说排行榜分析工具。自动采集四大榜单数据，生成趋势分析和创作建议。
  触发方式：/story-scan、/番茄扫描、「番茄数据」「番茄分析」
---

# Story Scan：番茄扫描

番茄小说市场数据分析师。采集排行榜数据，分析市场趋势，提供创作建议。

---

## 快速开始

```bash
cd .agents/skills/FanqieZhiShu

# 一键运行（爬虫+构建+启动看板）
python run.py all

# 或分步执行
python run.py scrape    # 采集数据
python run.py build     # 构建分析
python run.py serve     # 启动看板
```

---

## 核心命令

| 命令 | 功能 | 说明 |
|------|------|------|
| `python run.py scrape` | 采集数据 | 爬取番茄小说四大榜单 Top 30 |
| `python run.py build` | 构建分析 | 生成趋势数据、市场热点、作者分析 |
| `python run.py serve` | 启动看板 | 本地 HTTP 服务，端口 8000 |
| `python run.py all` | 完整流程 | 采集→构建→启动 |
| `python run.py status` | 查看状态 | 显示数据文件状态 |

---

## 看板地址

启动服务后访问：
- **榜单看板**: http://localhost:8000
- **趋势风向**: http://localhost:8000/trend.html
- **创作灵感**: http://localhost:8000/author.html

---

## 数据解读

### 榜单指标

| 指标 | 说明 | 重要性 |
|------|------|--------|
| 排名 | 当前在榜位置 | ★★★★★ |
| 阅读量 | 累计阅读人数 | ★★★★☆ |
| 排名变化 | 较昨日升降位次 | ★★★★☆ |
| 新上榜 | 是否为新进入榜单 | ★★★☆☆ |

### 趋势信号

| 信号 | 含义 | 创作建议 |
|------|------|----------|
| 新上榜增多 | 题材热度上升 | 考虑跟进，注意差异化 |
| 排名普遍上升 | 读者需求旺盛 | 可以深入研究该题材 |
| 阅读量激增 | 爆款出现 | 分析爆款特征，学习套路 |
| 排名普遍下降 | 题材热度下降 | 谨慎进入，避免同质化 |

---

## 常见操作

### 查看最新数据

```bash
# 查看男频新书榜
cat data/latest_male_new_ranks.json | head -100

# 查看市场总结
cat data/market_summary_male_new.json

# 查看题材趋势
cat data/author/theme_trends_male_new.json | head -100
```

### 重新抓取数据

```bash
# 清除任务状态，重新抓取
rm data/task_state_*.json
python run.py scrape
```

### 配置 AI 分析

创建 `.env` 文件：
```
API_BASE_URL=https://your-api-endpoint/v1
API_KEY=your-api-key
API_MODEL=your-model-name
```

---

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| 爬虫卡住 | 检查网络，或清除 `data/task_state_*.json` 重试 |
| 数据不更新 | 运行 `python run.py status` 查看状态 |
| 页面无法访问 | 确保服务已启动：`python run.py serve` |
| AI 分析不生效 | 检查 `.env` 配置，或使用规则摘要（默认） |

---

## 与网文创作集成

| 时机 | 跳转到 | 命令 |
|------|--------|------|
| 找到热门方向 | story-long-analyze | `/story-long-analyze` |
| 想写短篇 | story-short-scan | `/story-short-scan` |
| 直接开写 | story-long-write | `/story-long-write` |
| 查看详细扫榜 | story-long-scan | `/story-long-scan` |

---

## 项目结构

```
FanqieZhiShu/
├── run.py                      # 一键运行脚本
├── scrape_fanqie_ranks.py      # 爬虫脚本
├── scripts/build_latest.py     # 分析构建脚本
├── data/                       # 数据目录
│   ├── fanqie_*_ranks_*.json   # 原始快照
│   ├── latest_*_ranks.json     # 最新分析
│   ├── market_summary_*.json   # 市场热点
│   └── author/                 # 作者分析
├── api/latest/                 # 静态 API
└── *.html                      # 看板页面
```

---

## 与 test-rewrite 集成

`market-data/番茄女频市场数据.json` 是 rewrite 直接消费的市场数据文件，位于本 skill 目录下。

### 数据接口

| 字段 | 类型 | 用途 | rewrite 消费场景 |
|------|------|------|-----------------|
| `hot_genres` | array | 热门题材热度排行 | Phase 1 新书方案选题材 |
| `title_patterns` | object | 书名命名模式+示例 | Phase 1 新书方案定书名 |
| `tag_combinations` | object | 标签组合公式 | Phase 1 新书方案配标签 |
| `golden_three` | object | 黄金三章标准 | Phase 1.5 前3章检查 |
| `chapter_spec` | object | 章节字数/节奏标准 | Phase 2 写作参数 |
| `current_top_authors` | array | 顶流作者参考 | story-distill 蒸馏目标 |

### 更新方式

**手动同步**（推荐）：
```bash
python sync_market_data.py
```

**自动流程**：
```bash
# 1. 采集最新数据
python run.py scrape

# 2. 构建分析
python run.py build

# 3. 同步到test-rewrite
python sync_market_data.py
```

### 集成流程

```
story-scan 采集数据 → build 分析 → sync_market_data.py 同步 → test-rewrite Phase 1 读取
```