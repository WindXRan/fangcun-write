---
name: fanqie-hub
description: |
  番茄小说 Hub。集成下载器、排行榜爬虫、书库Web应用的统一入口。
  触发方式：/fanqie-hub、/下载小说、/番茄扫描、/启动书库、「下载XX」「扫描排行榜」「打开书库」
---

# fanqie-hub · 番茄小说 Hub

集成小说下载、排行榜采集、书库浏览的一站式工具。

## 快速使用

```bash
cd .agents/skills/fanqie-hub

# 下载小说
python run.py download "书名"
python run.py download-author "作者名"

# 采集排行榜
python run.py scan
python run.py build

# 启动Web服务
python run.py web

# 查看状态
python run.py status
```

## 功能模块

| 模块 | 说明 | 命令 |
|------|------|------|
| downloader/ | 番茄小说下载器（TomatoNovelDownloader） | `python run.py download` |
| scanner/ | 排行榜爬虫+数据分析 | `python run.py scan` |
| web/ | 书库Web应用（Flask） | `python run.py web` |
| projects/ | 共享书库目录 | 自动归档 |

## Web 服务

启动后访问 http://localhost:5000/

| 页面 | 路由 | 说明 |
|------|------|------|
| 书库首页 | `/` | 本地书库 + 番茄排行榜 |
| 阅读器 | `/book/<idx>` | 阅读指定书籍，支持版本切换 |
| 对比阅读 | `/compare` | 左右对照两个版本 |
| 番茄排行榜 | `/ranks/` | 榜单看板、趋势风向、创作灵感 |

## 下载器 API

下载器通过 HTTP API 通信（端口 18423）：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 服务器状态 |
| `/api/search?q=<keyword>` | GET | 搜索书籍 |
| `/api/preview/<book_id>` | GET | 预览书籍详情 |
| `/api/jobs` | POST | 创建下载任务 |

## 排行榜数据

```bash
# 采集最新数据
python run.py scan

# 构建分析
python run.py build

# 查看数据
cat scanner/data/latest_male_new_ranks.json
```

## 目录结构

```
fanqie-hub/
├── run.py                    # 统一入口
├── SKILL.md                  # 本文档
├── downloader/               # 下载器
│   ├── TomatoNovelDownloader-Win64-v2.4.11.exe
│   ├── config.yml
│   └── scripts/
├── scanner/                  # 排行榜爬虫
│   ├── scrape_fanqie_ranks.py
│   ├── run.py
│   ├── scripts/
│   └── data/
├── web/                      # Flask Web应用
│   ├── app.py
│   ├── templates/
│   ├── static/
│   └── tools/
└── projects/                 # 共享书库
    └── {作者名}/
        └── {书名}/
            └── _cache/
```

## 与 fangcun-novel 集成

fangcun-novel 的 pipeline.py 在写章完成后会自动启动书库服务。
