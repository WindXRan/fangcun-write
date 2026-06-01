# 番茄指数 · Fanqie Index

> 全方位追踪番茄小说四大榜单（男频新书/阅读、女频新书/阅读），每日自动抓取排行数据并结合 AI 生成趋势分析，部署为精美的在线看板。

---

## 快速开始

**新手？** 查看 [新手教程](TUTORIAL.md) 获取详细的图文说明。

**Windows 用户：** 双击运行 `setup.bat`，按照提示操作即可。

```bash
# 1. 克隆项目
git clone <仓库地址>
cd FanqieRankTracker

# 2. 运行一键脚本（Windows）
setup.bat
# 选择 [1] 首次安装 → [5] 完整流程

# 或手动操作
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python scrape_fanqie_ranks.py
python scripts/build_latest.py
python -m http.server 8000
```

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 自动爬取 | 每日定时抓取番茄小说各个分类的新书榜/阅读榜 Top 30 |
| 断点续传 | 爬虫支持中断恢复，通过 `task_state_*.json` 记录进度 |
| 字体反混淆 | 自动解码番茄小说的自定义字体加密（Unicode 0xE3E0 偏移密码） |
| 趋势对比 | 自动对比相邻两天数据：新上榜 / 掉榜 / 排名变化 / 阅读量增长 |
| AI 风向分析 | 接入 OpenAI 兼容 API，按分类生成市场趋势速评 |
| 类型风向标 | 独立趋势页聚合多日数据（7/14/30/全量天数），市场热度图表 |
| 创作灵感 | 作者分析页面，提供题材趋势、竞争分析、读者画像和创作建议 |
| 数据导出 | 支持 Excel (.xlsx)、CSV、JSON 三种格式导出 |
| 精美看板 | 暗色编辑风格仪表盘，带打字机动画和瀑布流书籍卡片 |
| 移动适配 | 完整的移动端适配，侧边栏抽屉式菜单 |
| 顶部导航 | 统一导航栏，一键切换四大榜单，齿轮图标可配置 API |
| 历史回看 | 日期选择器支持查看任意历史日期的榜单数据 |
| 数据接口 | 生成静态 JSON 接口，可按类型读取最新数据 |

---

## 食用指南

### 前置条件

- **Python 3.9+**
- **Git**（可选，用于版本管理）
- （可选）一个 OpenAI 兼容 API 的密钥，用于 AI 分析

### 第一步：克隆/下载项目

```bash
git clone <仓库地址>
cd FanqieRankTracker
```

或者直接下载 ZIP 解压。

### 第二步：安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 第三步：运行爬虫

```bash
# 爬取四大榜单（女频新书/阅读、男频新书/阅读），每个分类 Top 30
python scrape_fanqie_ranks.py
```

爬虫会自动发现所有分类，抓取数据保存到 `data/` 目录。

### 第四步：构建看板数据

```bash
# 不带 AI 分析（使用规则摘要）
python scripts/build_latest.py

# 带 AI 分析（需设置环境变量）
export API_BASE_URL="https://your-api-endpoint/v1"
export API_KEY="your-api-key"
export API_MODEL="your-model-name"
python scripts/build_latest.py
```

### 第五步：本地预览

```bash
python -m http.server 8000
```

打开浏览器访问 `http://localhost:8000`，顶部导航栏可切换四大榜单。

---

## API 配置

有两种方式配置 AI 分析的 API：

1. **环境变量**（构建脚本使用）：设置 `API_BASE_URL`、`API_KEY`、`API_MODEL`
2. **网页配置**（前端实时调用）：点击顶部导航栏右侧齿轮图标，在弹窗中填写并保存，数据存储在浏览器 localStorage 中

支持任何 OpenAI 兼容接口（如 Moonshot / DeepSeek / 自建服务等）。不配置 API 时，系统自动使用基于规则的摘要，**不影响核心功能**。

---

## 最新数据接口

构建脚本会生成静态 JSON 接口：

| 类型 | 路径 | 说明 |
|---|---|---|
| 类型索引 | `api/latest.json` | 返回所有可用类型及对应 URL |
| 全量数据 | `api/latest/{prefix}_all.json` | 指定榜单的全部分类、趋势和书籍 |
| 单类型数据 | `api/latest/{prefix}_{类型}.json` | 指定榜单的单个分类数据 |

其中 `{prefix}` 为 `female_new`、`female_read`、`male_new`、`male_read` 之一。

---

## 项目结构

```
FanqieZhiShu/
├── scrape_fanqie_ranks.py      # 番茄小说爬虫（Playwright）
├── verify_font_mapping.py      # 字体映射验证工具
├── setup.bat                   # Windows 一键安装脚本
├── requirements.txt            # Python 依赖
├── .env / .env.example         # 环境变量配置
│
├── scripts/
│   ├── build_latest.py         # 趋势对比 + AI 分析构建脚本
│   └── migrate_md_to_json.py   # 一次性迁移工具
│
├── js/
│   ├── config.js               # 榜单类型注册表 + URL 参数解析
│   ├── nav.js                  # 顶部导航栏 + API 配置弹窗
│   ├── utils.js                # 共享工具函数（escapeHtml/Markdown渲染等）
│   ├── app.js                  # 主榜单页面逻辑
│   ├── trend.js                # 趋势风向标页面逻辑
│   ├── author.js               # 创作灵感页面逻辑
│   └── export.js               # 数据导出功能（CSV/Excel/JSON）
│
├── css/
│   ├── style.css               # 暗色编辑风格主题样式
│   └── author.css              # 创作灵感页专用样式
│
├── index.html                  # 仪表盘入口页
├── trend.html                  # 类型风向标趋势分析页
├── author.html                 # 创作灵感页
│
├── data/                       # 数据目录（自动生成）
│   ├── fanqie_{prefix}_ranks_YYYYMMDD.json  # 每日原始快照
│   ├── latest_{prefix}_ranks.json           # 最新聚合数据
│   ├── market_summary_{prefix}.json         # 全站热点总结
│   ├── dates_{prefix}.json                  # 日期索引
│   ├── task_state_{prefix}_YYYYMMDD.json    # 爬虫状态恢复文件
│   ├── trends/
│   │   └── {prefix}_YYYY-MM-DD.json         # 趋势归档
│   └── author/
│       ├── theme_trends_{prefix}.json       # 题材趋势
│       ├── competitive_analysis_{prefix}.json # 竞品分析
│       ├── reader_profile_{prefix}.json     # 读者画像
│       └── creation_suggestions_{prefix}.json # 创作建议
│
├── api/latest/                 # 最新数据静态接口
│   ├── {prefix}_all.json       # 全量数据
│   ├── {prefix}_index.json     # 分类索引
│   └── {prefix}_{category}.json # 单分类数据
│
├── README.md                   # 本文件
├── README_EN.md                # 英文文档
├── TUTORIAL.md                 # 新手教程
├── 使用教程.md                  # 详细使用教程
└── PROJECT_MAP.md              # 项目图谱
```

---

## 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据采集层                                │
│  Playwright 爬虫 ──→ 解码字体混淆 ──→ 保存每日快照 JSON          │
│  (scrape_fanqie_ranks.py)     (data/fanqie_*_YYYYMMDD.json)     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据处理层                                │
│  build_latest.py ──→ 趋势对比 ──→ AI摘要(可选) ──→ 输出聚合数据  │
│  (scripts/build_latest.py)                                      │
│     ↓              ↓              ↓              ↓              │
│  latest_*.json   trends/      market_summary  api/latest/      │
│                                  data/author/                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        前端展示层                                │
│  index.html ──→ app.js      (榜单看板：分类/书籍/趋势/AI摘要)   │
│  trend.html ──→ trend.js    (趋势风向标：多周期分析/市场热度)    │
│  author.html ──→ author.js  (创作灵感：题材/竞品/读者/建议)      │
│  共享模块：config.js / nav.js / utils.js / export.js            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 常见问题

**Q: 爬虫运行很慢怎么办？**
每个榜单需要爬取多个分类，每个分类需要滚动加载，完整运行约 10-15 分钟属正常。可以修改 `scrape_fanqie_ranks.py` 中的 `RANK_CONFIGS` 只保留需要的榜单。

**Q: 爬虫中断了怎么办？**
直接重新运行 `python scrape_fanqie_ranks.py`，爬虫会自动从上次中断的地方继续。进度保存在 `data/task_state_*.json` 文件中。

**Q: 不配置 AI 也能用吗？**
可以！系统会自动 fallback 到基于规则的摘要（如"新增3本上榜；《XX》排名上升+5位"）。只是没有 AI 自然语言分析而已。

**Q: 可以换成其他榜单吗？**
可以，修改 `scrape_fanqie_ranks.py` 中的 `RANK_CONFIGS`，调整 gender、type 和 entry_cat 即可。

**Q: 如何查看历史数据？**
在榜单页面底部使用日期导航，点击 `◀` `▶` 切换日期，或点击日期数字打开日历选择器跳转到指定日期。

**Q: 数据文件越来越大怎么办？**
- `data/fanqie_*_ranks_YYYYMMDD.json` 是每日快照，可以删除不需要的历史日期
- `data/trends/` 是趋势归档，可以清理早期文件
- 删除数据后，对应日期的趋势分析将不可用

**Q: 如何定时自动运行？**
- Windows：使用任务计划程序，设置每天定时运行爬虫和构建脚本
- Linux/Mac：使用 cron 定时任务
- 详见 [TUTORIAL.md](TUTORIAL.md) 中的"进阶使用"章节

---

## License

MIT
