# 番茄指数 (FanqieRankTracker) 项目图谱

> 生成时间：2026-05-29
> 项目路径：C:\mimo\FanqieZhiShu

---

## 一、项目概述

**番茄指数**是一个自动化的小说榜单追踪和分析系统，用于监控番茄小说平台的四大排行榜（男频新书榜、男频阅读榜、女频新书榜、女频阅读榜）。

### 核心能力
- **数据采集**：使用 Playwright 无头浏览器抓取番茄小说榜单数据
- **趋势分析**：对比历史数据，计算排名变化、新上榜、掉榜等趋势
- **AI 摘要**：可选调用 LLM API 生成智能分析报告
- **可视化看板**：纯静态前端展示榜单、趋势、创作灵感

### 技术栈
| 层级 | 技术 |
|------|------|
| 爬虫 | Python + Playwright |
| 数据处理 | Python (JSON) |
| AI 集成 | OpenAI 兼容 API |
| 前端 | 原生 HTML/CSS/JS |
| 部署 | 静态文件服务 |

---

## 二、目录结构

```
FanqieZhiShu/
├── scrape_fanqie_ranks.py      # 爬虫主程序 (399行)
├── verify_font_mapping.py      # 字体映射验证工具
├── setup.bat                   # Windows 安装脚本
├── requirements.txt            # Python 依赖
├── .env / .env.example         # 环境变量配置
│
├── scripts/
│   ├── build_latest.py         # 数据构建引擎 (1860行)
│   └── migrate_md_to_json.py   # 一次性迁移工具
│
├── js/
│   ├── config.js               # 榜单类型注册表 + URL参数解析
│   ├── nav.js                  # 顶部导航栏 + API配置弹窗
│   ├── app.js                  # 主榜单页逻辑
│   ├── trend.js                # 趋势风向标页逻辑
│   ├── author.js               # 创作灵感页逻辑
│   ├── export.js               # 数据导出功能
│   └── utils.js                # 共享工具函数
│
├── css/
│   ├── style.css               # 主题样式 (2137行)
│   └── author.css              # 创作灵感页样式
│
├── index.html                  # 主榜单页入口
├── trend.html                  # 趋势风向标页入口
├── author.html                 # 创作灵感页入口
│
├── data/                       # 数据存储目录
│   ├── fanqie_{prefix}_ranks_YYYYMMDD.json  # 每日原始快照
│   ├── latest_{prefix}_ranks.json           # 最新聚合数据
│   ├── dates_{prefix}.json                  # 日期索引
│   ├── market_summary_{prefix}.json         # 市场热点分析
│   ├── task_state_{prefix}_YYYYMMDD.json    # 爬虫状态恢复
│   ├── trends/                              # 趋势归档
│   │   └── {prefix}_YYYY-MM-DD.json
│   └── author/                              # 作者分析数据
│       ├── theme_trends_{prefix}.json
│       ├── competitive_analysis_{prefix}.json
│       ├── reader_profile_{prefix}.json
│       └── creation_suggestions_{prefix}.json
│
└── api/latest/                 # 静态 JSON 接口
    ├── {prefix}_all.json
    ├── {prefix}_index.json
    └── {prefix}_{category}.json
```

---

## 三、核心模块详解

### 3.1 爬虫模块 (`scrape_fanqie_ranks.py`)

**职责**：抓取番茄小说四大榜单的 Top 30 书籍数据

**关键组件**：
```python
CHAR_SEQUENCE = [...]  # 380个字符的映射表，用于解码番茄自定义字体
START_CODE = 58344     # 0xE3E0，Unicode 偏移起始值

RANK_CONFIGS = [
    {"gender": 1, "type": 1, "name": "男频新书榜", "prefix": "male_new",    "entry_cat": "1141"},
    {"gender": 1, "type": 2, "name": "男频阅读榜", "prefix": "male_read",   "entry_cat": "1141"},
    {"gender": 0, "type": 1, "name": "女频新书榜", "prefix": "female_new",  "entry_cat": "1139"},
    {"gender": 0, "type": 2, "name": "女频阅读榜", "prefix": "female_read", "entry_cat": "1139"},
]
```

**核心函数**：
- `decode_text(text)` - 解码番茄自定义字体混淆
- `scrape_rank_type(page, rank_config)` - 抓取指定类型排行榜
- 状态恢复机制：通过 `task_state_*.json` 实现中断续爬

**输出**：`data/fanqie_{prefix}_ranks_YYYYMMDD.json`

---

### 3.2 数据构建引擎 (`scripts/build_latest.py`)

**职责**：处理原始快照，生成趋势数据和分析报告

**核心函数**：
- `parse_reads(reads_str)` - 解析阅读量字符串（如 "15.2万"）
- `load_snapshot(path)` - 加载 JSON 快照
- `compare_categories(today, prev)` - 对比两天数据计算趋势
- `generate_ai_summary(...)` - 调用 LLM 生成 AI 摘要
- `build_market_summary(...)` - 构建多周期市场热点分析
- `build_author_analysis(...)` - 生成作者创作灵感数据

**处理流程**：
```
加载快照 → 趋势对比 → AI摘要(可选) → 输出聚合数据
    ↓           ↓           ↓             ↓
  raw.json   trends/    market_summary  latest_*.json
                                       api/latest/
                                       data/author/
```

**输出文件**：
- `data/latest_{prefix}_ranks.json` - 最新聚合数据
- `data/trends/{prefix}_YYYY-MM-DD.json` - 趋势归档
- `data/market_summary_{prefix}.json` - 市场热点
- `data/author/*_{prefix}.json` - 作者分析
- `api/latest/` - 静态 JSON 接口

---

### 3.3 前端模块

#### 3.3.1 配置层 (`js/config.js`)
```javascript
RANK_TYPES = {
    male_new:    { name: "男频新书榜", prefix: "male_new",    gender: "男频" },
    male_read:   { name: "男频阅读榜", prefix: "male_read",   gender: "男频" },
    female_new:  { name: "女频新书榜", prefix: "female_new",  gender: "女频" },
    female_read: { name: "女频阅读榜", prefix: "female_read", gender: "女频" },
}
```
- 通过 `?rank=` URL 参数切换榜单类型
- 所有页面共享此配置

#### 3.3.2 导航层 (`js/nav.js`)
- 注入统一顶部导航栏
- 四大榜单 Tab 切换
- 趋势/灵感/榜单页面跳转
- API 配置弹窗（齿轮图标）

#### 3.3.3 主榜单页 (`js/app.js`)
- 侧边栏分类导航
- 日期选择器（支持历史回看）
- 瀑布流书籍卡片展示
- 趋势标签（新上榜/排名变化/阅读量增长）
- AI 摘要打字机效果
- 书籍信息复制功能

#### 3.3.4 趋势风向标 (`js/trend.js`)
- 多周期分析（7/14/30/全量天数）
- 市场热度图表
- 每日新书/涨幅/阅读量排行
- 分类趋势评分

#### 3.3.5 创作灵感 (`js/author.js`)
- 题材趋势分析
- 竞争分析（饱和度/机会指数）
- 读者画像
- 创作建议

#### 3.3.6 数据导出 (`js/export.js`)
- 支持 CSV、Excel (.xlsx)、JSON 三种格式
- 全局 Toast 通知

#### 3.3.7 工具函数 (`js/utils.js`)
- `escapeHtml(str)` - HTML 转义
- `escapeAttr(str)` - 属性值转义
- `renderMarkdown(text)` - 简易 Markdown 渲染
- `parseReads(readsStr)` - 解析阅读量

---

## 四、数据流图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据采集层                                      │
│  ┌─────────────────────┐                                                   │
│  │ scrape_fanqie_ranks │ ──→ data/fanqie_{prefix}_ranks_YYYYMMDD.json     │
│  │      .py            │     (每日原始快照)                                  │
│  └─────────────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据处理层                                      │
│  ┌─────────────────────┐                                                   │
│  │   build_latest.py   │ ──→ data/latest_{prefix}_ranks.json (聚合数据)    │
│  │                     │ ──→ data/trends/{prefix}_YYYY-MM-DD.json (趋势)   │
│  │                     │ ──→ data/market_summary_{prefix}.json (市场热点)  │
│  │                     │ ──→ data/author/*_{prefix}.json (作者分析)        │
│  │                     │ ──→ api/latest/ (静态JSON接口)                    │
│  └─────────────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端展示层                                      │
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                              │
│  │index.html│    │trend.html│    │author.html│                             │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘                              │
│       │               │               │                                     │
│       ▼               ▼               ▼                                     │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                                │
│  │ app.js  │    │trend.js │    │author.js│                                 │
│  └────┬────┘    └────┬────┘    └────┬────┘                                │
│       │               │               │                                     │
│       └───────────────┼───────────────┘                                     │
│                       ▼                                                     │
│              ┌─────────────────┐                                            │
│              │  config.js      │ (榜单配置)                                 │
│              │  nav.js         │ (导航栏)                                   │
│              │  utils.js       │ (工具函数)                                 │
│              │  export.js      │ (数据导出)                                 │
│              └─────────────────┘                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 五、文件依赖关系

### 5.1 Python 模块依赖

```
scrape_fanqie_ranks.py
    ├── playwright (外部依赖)
    ├── json, os, sys, time, datetime (标准库)
    └── 输出 → data/fanqie_*.json

scripts/build_latest.py
    ├── dotenv (可选，加载.env)
    ├── json, os, glob, argparse (标准库)
    ├── urllib.parse (URL编码)
    └── 输入 ← data/fanqie_*.json
    └── 输出 → data/latest_*.json, data/trends/, api/latest/, data/author/
```

### 5.2 JavaScript 模块依赖

```
index.html
    ├── js/config.js      (榜单配置)
    ├── js/nav.js         (依赖 config.js)
    ├── js/utils.js       (工具函数)
    ├── js/export.js      (依赖 utils.js)
    └── js/app.js         (依赖 config.js, utils.js)

trend.html
    ├── js/config.js
    ├── js/nav.js
    ├── js/utils.js
    ├── js/export.js
    └── js/trend.js       (依赖 config.js, utils.js)

author.html
    ├── js/config.js
    ├── js/nav.js
    ├── js/utils.js
    ├── js/export.js
    └── js/author.js      (依赖 config.js, utils.js)
```

### 5.3 数据文件依赖

```
前端页面加载的数据文件：

index.html (app.js)
    ├── data/latest_{prefix}_ranks.json
    ├── data/dates_{prefix}.json
    └── api/latest/{prefix}_{category}.json

trend.html (trend.js)
    ├── data/dates_{prefix}.json
    ├── api/latest.json
    ├── api/latest/{prefix}_all.json
    └── data/market_summary_{prefix}.json

author.html (author.js)
    ├── data/author/theme_trends_{prefix}.json
    ├── data/author/competitive_analysis_{prefix}.json
    ├── data/author/reader_profile_{prefix}.json
    ├── data/author/creation_suggestions_{prefix}.json
    └── data/latest_{prefix}_ranks.json
```

---

## 六、数据文件格式

### 6.1 每日快照 (`fanqie_{prefix}_ranks_YYYYMMDD.json`)

```json
{
  "date": "2026-05-29",
  "rank_type": "female_new",
  "categories": [
    {
      "name": "豪门总裁",
      "books": [
        {
          "rank": 1,
          "title": "书名",
          "author": "作者",
          "reads": "15.2万",
          "intro": "简介",
          "url": "链接",
          "word_count": "100万字"
        }
      ]
    }
  ]
}
```

### 6.2 聚合数据 (`latest_{prefix}_ranks.json`)

包含趋势标签：
- `new_arrivals` - 新上榜书籍
- `dropped` - 掉榜书籍
- `rank_changes` - 排名变化
- `reads_growth` - 阅读量增长

### 6.3 市场热点 (`market_summary_{prefix}.json`)

多周期分析（7/14/30/全量天数）：
- 热门题材
- 热门类型
- 热门关键词

### 6.4 作者分析 (`data/author/*.json`)

- `theme_trends` - 题材趋势
- `competitive_analysis` - 竞争分析（饱和度、机会指数）
- `reader_profile` - 读者画像
- `creation_suggestions` - 创作建议

---

## 七、API 接口

### 7.1 静态 JSON 接口 (`api/latest/`)

| 接口路径 | 说明 |
|----------|------|
| `{prefix}_all.json` | 该榜单所有分类的完整数据 |
| `{prefix}_index.json` | 该榜单的分类索引 |
| `{prefix}_{category}.json` | 指定分类的数据 |

**prefix 取值**：`male_new`, `male_read`, `female_new`, `female_read`

### 7.2 AI API 配置

通过环境变量配置：
```bash
API_BASE_URL=https://api.example.com/v1
API_KEY=your_api_key
API_MODEL=model_name
```

前端可通过齿轮图标配置，存储于 localStorage。

---

## 八、运行命令

```bash
# 环境安装
pip install -r requirements.txt
playwright install chromium

# 运行爬虫（抓取四大榜单 Top 30，耗时 10-15 分钟）
python scrape_fanqie_ranks.py

# 构建看板数据
python scripts/build_latest.py                    # 纯规则摘要
API_BASE_URL=... API_KEY=... API_MODEL=... python scripts/build_latest.py  # 带AI分析

# 本地预览
python -m http.server 8000   # 访问 http://localhost:8000
```

---

## 九、代码统计

| 文件类型 | 文件数 | 总行数 |
|----------|--------|--------|
| Python (.py) | 4 | 2,304 |
| JavaScript (.js) | 7 | 2,687 |
| CSS (.css) | 2 | 3,041 |
| HTML (.html) | 3 | 430 |
| **总计** | **16** | **8,462** |

---

## 十、关键设计点

### 10.1 字体反混淆

番茄小说使用自定义字体混淆技术，通过 Unicode 偏移（0xE3E0 起始）映射真实字符。`CHAR_SEQUENCE` 表包含 380 个映射字符。

### 10.2 状态恢复

爬虫支持中断恢复：
- `task_state_{prefix}_{date}.json` 记录已完成的分类
- 重启后自动跳过已完成部分

### 10.3 缓存策略

前端使用 10 分钟缓存失效：
```javascript
const cacheBuster = `v=${Math.floor(Date.now() / 600000)}`;
```

### 10.4 多榜单支持

通过 URL 参数 `?rank=` 实现四大榜单切换，所有页面共享同一套代码。

---

## 十一、文件清单

### 源代码文件

| 文件路径 | 行数 | 说明 |
|----------|------|------|
| `scrape_fanqie_ranks.py` | 399 | 爬虫主程序 |
| `scripts/build_latest.py` | 1860 | 数据构建引擎 |
| `scripts/migrate_md_to_json.py` | - | 迁移工具（一次性） |
| `verify_font_mapping.py` | - | 字体验证工具 |
| `js/config.js` | 42 | 榜单配置 |
| `js/nav.js` | 171 | 导航栏 |
| `js/app.js` | 659 | 主榜单页 |
| `js/trend.js` | 530 | 趋势页 |
| `js/author.js` | 775 | 创作灵感页 |
| `js/export.js` | 465 | 数据导出 |
| `js/utils.js` | 45 | 工具函数 |
| `css/style.css` | 2137 | 主题样式 |
| `css/author.css` | 904 | 创作灵感样式 |
| `index.html` | 105 | 主榜单入口 |
| `trend.html` | 122 | 趋势页入口 |
| `author.html` | 203 | 创作灵感入口 |

### 配置文件

| 文件路径 | 说明 |
|----------|------|
| `requirements.txt` | Python 依赖 |
| `.env` / `.env.example` | 环境变量 |
| `.gitignore` | Git 忽略规则 |
| `CLAUDE.md` | Claude Code 指引 |
| `README.md` / `README_EN.md` | 项目文档 |
| `TUTORIAL.md` / `使用教程.md` | 使用教程 |
| `setup.bat` | Windows 安装脚本 |

---

## 十二、扩展点

1. **新增榜单**：修改 `RANK_CONFIGS`（Python）和 `RANK_TYPES`（JS）
2. **新增分析维度**：在 `build_latest.py` 中添加分析函数
3. **自定义主题**：修改 `css/style.css` 中的 CSS 变量
4. **接入其他 AI**：修改 `build_latest.py` 中的 API 调用逻辑

---

*此文档由 Claude Code 自动生成，反映项目当前状态。*
