# 番茄指数 - 新手教程

本教程将带你从零开始搭建番茄指数，即使你没有任何编程经验也能轻松上手。

---

## 目录

1. [环境准备](#1-环境准备)
2. [一键安装](#2-一键安装)
3. [运行爬虫](#3-运行爬虫)
4. [配置 AI 服务](#4-配置-ai-服务)
5. [构建看板](#5-构建看板)
6. [本地预览](#6-本地预览)
7. [常见问题](#7-常见问题)
8. [API 配置示例](#8-api-配置示例)

---

## 1. 环境准备

### 1.1 安装 Python

番茄指数需要 Python 3.9 或更高版本。

**下载地址：** https://www.python.org/downloads/

**安装步骤：**

1. 打开上面的下载地址，点击 "Download Python 3.x.x" 按钮
2. 运行下载的安装程序
3. **重要：** 勾选底部的 "Add Python to PATH" 选项
4. 点击 "Install Now" 开始安装
5. 等待安装完成

**验证安装：**

打开命令提示符（按 Win+R，输入 `cmd`，回车），输入：

```bash
python --version
```

如果显示 `Python 3.x.x`，说明安装成功。

### 1.2 安装 Git（可选）

Git 用于版本管理，不是必须的。如果你只是想使用番茄指数，可以跳过这一步。

**下载地址：** https://git-scm.com/downloads

---

## 2. 一键安装

### 2.1 下载项目

**方式一：使用 Git（推荐）**

```bash
git clone https://github.com/your-username/FanqieRankTracker.git
cd FanqieRankTracker
```

**方式二：直接下载**

1. 在 GitHub 页面点击绿色的 "Code" 按钮
2. 选择 "Download ZIP"
3. 解压下载的 ZIP 文件
4. 进入解压后的文件夹

### 2.2 运行安装脚本

**Windows 用户：**

双击运行 `setup.bat` 脚本，按照提示操作：

```
╔══════════════════════════════════════════════════════════╗
║           番茄指数 FanqieRankTracker - 一键启动          ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║   [1] 首次安装（安装依赖 + 配置环境）                    ║
║   [2] 运行爬虫（抓取今日数据）                          ║
║   [3] 构建看板（生成趋势分析）                          ║
║   [4] 启动预览（本地打开看板）                          ║
║   [5] 完整流程（爬虫 + 构建 + 预览）                    ║
║   [6] 配置 AI 服务                                      ║
║   [0] 退出                                              ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

选择 `[1] 首次安装`，脚本会自动：

- 检查 Python 是否已安装
- 创建虚拟环境
- 安装所有依赖
- 安装 Playwright 浏览器

**Mac/Linux 用户：**

打开终端，进入项目目录，执行：

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

---

## 3. 运行爬虫

爬虫会自动抓取番茄小说四大榜单的数据：

- 女频新书榜
- 女频阅读榜
- 男频新书榜
- 男频阅读榜

每个榜单抓取 18-19 个分类，每个分类 Top 30 本书，完整运行约 10-15 分钟。

### 使用一键脚本

在 `setup.bat` 中选择 `[2] 运行爬虫`。

### 手动运行

```bash
# 确保虚拟环境已激活
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 运行爬虫
python scrape_fanqie_ranks.py
```

### 爬虫输出

爬虫运行完成后，会在 `data/` 目录生成以下文件：

```
data/
├── fanqie_female_new_ranks_20260528.json    # 女频新书榜数据
├── fanqie_female_read_ranks_20260528.json   # 女频阅读榜数据
├── fanqie_male_new_ranks_20260528.json      # 男频新书榜数据
└── fanqie_male_read_ranks_20260528.json     # 男频阅读榜数据
```

---

## 4. 配置 AI 服务

AI 服务用于生成智能趋势分析摘要。**不配置也可以正常使用**，系统会使用规则摘要替代。

### 4.1 支持的 AI 服务

番茄指数支持任何 OpenAI 兼容的 API，包括：

| 服务 | API_BASE_URL | API_MODEL 示例 |
|------|--------------|----------------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 硅基流动 | `https://api.siliconflow.cn/v1` | `Qwen/Qwen2-7B-Instruct` |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2:7b` |

### 4.2 配置方式

**方式一：使用一键脚本（推荐）**

在 `setup.bat` 中选择 `[6] 配置 AI 服务`，按提示输入即可。

**方式二：手动创建 .env 文件**

在项目根目录创建 `.env` 文件，内容如下：

```
API_BASE_URL=https://api.deepseek.com/v1
API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
API_MODEL=deepseek-chat
```

**方式三：设置环境变量**

```bash
# Windows CMD
set API_BASE_URL=https://api.deepseek.com/v1
set API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
set API_MODEL=deepseek-chat

# Windows PowerShell
$env:API_BASE_URL="https://api.deepseek.com/v1"
$env:API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
$env:API_MODEL="deepseek-chat"

# Mac/Linux
export API_BASE_URL=https://api.deepseek.com/v1
export API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
export API_MODEL=deepseek-chat
```

**方式四：在网页中配置**

启动看板后，点击顶部导航栏右侧的齿轮图标，在弹窗中填写 API 配置。

---

## 5. 构建看板

构建脚本会读取爬虫抓取的数据，生成趋势分析、市场热点、作者分析等数据。

### 使用一键脚本

在 `setup.bat` 中选择 `[3] 构建看板`。

### 手动运行

```bash
# 确保虚拟环境已激活

# 不带 AI 分析（使用规则摘要）
python scripts/build_latest.py

# 带 AI 分析（需要先配置 API）
python scripts/build_latest.py
```

### 构建输出

构建完成后，会生成以下文件：

```
data/
├── latest_female_new_ranks.json    # 最新聚合数据
├── market_summary_female_new.json  # 市场热点分析
├── dates_female_new.json           # 日期索引
├── trends/                         # 趋势归档
│   └── female_new_2026-05-28.json
└── author/                         # 作者分析数据
    ├── theme_trends_female_new.json
    ├── competitive_analysis_female_new.json
    ├── reader_profile_female_new.json
    └── creation_suggestions_female_new.json

api/latest/
├── female_new_all.json             # 全量数据接口
├── female_new_index.json           # 分类索引接口
└── female_new_古风世情.json         # 单分类数据接口
```

---

## 6. 本地预览

### 使用一键脚本

在 `setup.bat` 中选择 `[4] 启动预览`，浏览器会自动打开。

### 手动运行

```bash
# 启动本地服务器
python -m http.server 8000
```

然后在浏览器中打开：http://localhost:8000

### 页面说明

| 页面 | 功能 |
|------|------|
| 首页 (index.html) | 主榜单看板，显示书籍列表、趋势标签、AI 摘要 |
| 风向标 (trend.html) | 多日趋势分析，显示市场热度、上榜波动 |
| 创作灵感 (author.html) | 作者分析工具，显示题材趋势、竞品分析、读者画像 |

### 切换榜单

点击顶部导航栏的四个按钮，可以切换不同榜单：

- 男频新书榜
- 男频阅读榜
- 女频新书榜
- 女频阅读榜

---

## 7. 常见问题

### Q1: Python 命令找不到

**问题：** 输入 `python --version` 提示"不是内部或外部命令"

**解决：**
1. 重新安装 Python，确保勾选 "Add Python to PATH"
2. 或者尝试使用 `python3` 命令
3. 重启命令提示符后再试

### Q2: pip 安装失败

**问题：** `pip install` 时报错

**解决：**
1. 检查网络连接
2. 尝试使用国内镜像：
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

### Q3: Playwright 安装失败

**问题：** `playwright install chromium` 报错

**解决：**
1. 检查网络连接
2. 尝试使用代理
3. 手动下载浏览器：https://playwright.dev/python/docs/browsers

### Q4: 爬虫运行很慢

**问题：** 爬虫运行超过 15 分钟

**解决：**
1. 这是正常的，每个分类需要滚动加载
2. 如果只想抓取部分榜单，可以修改 `scrape_fanqie_ranks.py` 中的 `RANK_CONFIGS`

### Q5: 数据加载失败

**问题：** 看板显示"数据加载失败"

**解决：**
1. 确保已经运行过爬虫和构建脚本
2. 检查 `data/` 目录下是否有数据文件
3. 尝试刷新页面

### Q6: AI 分析没有生成

**问题：** 构建后没有 AI 分析

**解决：**
1. 检查是否配置了 AI 服务（.env 文件或环境变量）
2. 检查 API_KEY 是否正确
3. 检查网络连接
4. 不配置 AI 也可以正常使用，系统会使用规则摘要

### Q7: 端口被占用

**问题：** `python -m http.server 8000` 报端口占用

**解决：**
1. 使用其他端口：`python -m http.server 8080`
2. 或者关闭占用 8000 端口的程序

---

## 8. API 配置示例

### 8.1 DeepSeek（推荐国内用户）

```
API_BASE_URL=https://api.deepseek.com/v1
API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
API_MODEL=deepseek-chat
```

**获取 API Key：** https://platform.deepseek.com/api_keys

### 8.2 OpenAI

```
API_BASE_URL=https://api.openai.com/v1
API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
API_MODEL=gpt-4o-mini
```

**获取 API Key：** https://platform.openai.com/api-keys

### 8.3 硅基流动 SiliconFlow

```
API_BASE_URL=https://api.siliconflow.cn/v1
API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
API_MODEL=Qwen/Qwen2-7B-Instruct
```

**获取 API Key：** https://cloud.siliconflow.cn/account/ak

### 8.4 本地 Ollama

如果你在本地安装了 Ollama，可以使用本地模型：

```
API_BASE_URL=http://localhost:11434/v1
API_KEY=ollama
API_MODEL=qwen2:7b
```

**安装 Ollama：** https://ollama.com/download

---

## 9. 进阶使用

### 9.1 定时运行爬虫

可以使用 Windows 任务计划程序或 Linux cron 定时运行爬虫：

**Windows 任务计划程序：**

1. 打开"任务计划程序"（按 Win 搜索"任务计划程序"）
2. 点击"创建基本任务"
3. 设置名称（如"番茄指数爬虫"）和触发器（每天 08:00）
4. 设置操作为"启动程序"：
   - 程序：`python`
   - 参数：`scrape_fanqie_ranks.py`
   - 起始于：项目目录路径（如 `C:\mimo\FanqieZhiShu`）
5. 完成创建

**Linux/Mac cron：**

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天 08:00 运行爬虫和构建）
0 8 * * * cd /path/to/FanqieZhiShu && /path/to/venv/bin/python scrape_fanqie_ranks.py && /path/to/venv/bin/python scripts/build_latest.py
```

### 9.2 部署到 GitHub Pages

1. Fork 本项目到你的 GitHub 账号
2. 在仓库设置中启用 GitHub Pages
3. 选择 `main` 分支和 `/ (root)` 目录
4. 等待几分钟，即可通过 `https://your-username.github.io/FanqieZhiShu/` 访问

**注意：** GitHub Pages 是静态托管，无法运行 Python 爬虫。需要在本地运行爬虫和构建脚本，然后将生成的文件推送到 GitHub。

### 9.3 自定义榜单

如果你想追踪其他榜单，可以修改 `scrape_fanqie_ranks.py` 中的 `RANK_CONFIGS`：

```python
RANK_CONFIGS = [
    {"gender": 1, "type": 1, "name": "男频新书榜", "prefix": "male_new", "entry_cat": "1141"},
    {"gender": 1, "type": 2, "name": "男频阅读榜", "prefix": "male_read", "entry_cat": "1141"},
    {"gender": 0, "type": 1, "name": "女频新书榜", "prefix": "female_new", "entry_cat": "1139"},
    {"gender": 0, "type": 2, "name": "女频阅读榜", "prefix": "female_read", "entry_cat": "1139"},
    # 添加更多榜单...
]
```

参数说明：
- `gender`: 0=女频, 1=男频
- `type`: 1=新书榜, 2=阅读榜
- `prefix`: 数据文件前缀（用于命名文件）
- `entry_cat`: 该榜单的首个分类 ID（需要在番茄小说网站上查找）

### 9.4 验证字体映射

如果爬虫抓取的数据出现乱码，可以使用 `verify_font_mapping.py` 验证字体映射是否正确：

```bash
python verify_font_mapping.py
```

该工具会检查番茄小说的自定义字体加密是否被正确解码。

### 9.5 数据清理

随着使用时间增长，数据文件会越来越多。以下是清理建议：

```bash
# 查看数据目录大小
du -sh data/

# 删除 30 天前的每日快照（Windows）
forfiles /p data /m fanqie_*_ranks_*.json /d -30 /c "cmd /c del @path"

# 删除 30 天前的趋势归档（Linux/Mac）
find data/trends/ -name "*.json" -mtime +30 -delete
```

**注意：** 删除数据后，对应日期的趋势分析将不可用。建议保留最近 30 天的数据。

---

## 10. 获取帮助

如果遇到问题，可以：

1. 查看本文档的[常见问题](#7-常见问题)部分
2. 在 GitHub 上提交 Issue
3. 查看项目的 README.md 文件

---

**祝你使用愉快！**
