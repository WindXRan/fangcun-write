---
name: novel-download
description: |
  小说下载工具。通过 TomatoNovelDownloader server HTTP API 下载番茄小说，按作者名自动归档到 projects/ 目录。
  触发方式：/novel-download、/下载小说、「下载这本小说」「帮我下载XX」
---

# novel-download · 小说下载归档

## 目录结构

```
.agents/skills/novel-download/
├── TomatoNovelDownloader-Win64-v2.4.11.exe
├── config.yml
├── scripts/
│   ├── archive_novel.py
│   ├── download_by_author.ps1    # 按作者批量下载
│   └── download_book.ps1         # 单本下载（书名/ID/链接）
├── downloads/                    # 下载临时目录
├── projects/                     # 归档目录（永久，公共缓存）
│   └── {作者名}/
│       ├── {书名}.txt
│       └── {书名}/
│           ├── original.txt
│           └── _cache/
│               ├── chapters/
│               └── analysis/
└── SKILL.md
```

## 快速使用

### 单本下载（推荐）

```powershell
# 按书名搜索下载
powershell -ExecutionPolicy Bypass -File scripts/download_book.ps1 -Query "惊华庭"

# 按 book_id 下载
powershell -ExecutionPolicy Bypass -File scripts/download_book.ps1 -Query "7611913437316140057"

# 按链接下载
powershell -ExecutionPolicy Bypass -File scripts/download_book.ps1 -Query "https://fanqienovel.com/page/7611913437316140057"

# 指定章节范围
powershell -ExecutionPolicy Bypass -File scripts/download_book.ps1 -Query "惊华庭" -Range "1-50"
```

### 按作者批量下载

```powershell
powershell -ExecutionPolicy Bypass -File scripts/download_by_author.ps1 -Author "初点点"

# 指定章节范围
powershell -ExecutionPolicy Bypass -File scripts/download_by_author.ps1 -Author "初点点" -Range "1-100"
```

## 公共缓存机制

源文拆章和分析结果放在 `projects/{作者名}/{书名}/_cache/` 目录下，多个仿写项目共用。

## HTTP API 参考

所有脚本通过 HTTP API 与 TomatoNovelDownloader server 通信，**不依赖 Chrome/CDP**。

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 服务器状态 |
| `/api/search?q=<keyword>` | GET | 搜索（返回 `{ items: [{title, author, book_id}] }`） |
| `/api/preview/<book_id>` | GET | 预览（返回书籍详情） |
| `/api/jobs` | GET | 列出下载任务 |
| `/api/jobs` | POST | 创建下载任务（`{book_id, range_start?, range_end?}`） |
| `/api/jobs/<id>/cancel` | POST | 取消任务 |
| `/api/history` | GET | 下载历史 |
| `/api/config` | GET | 快捷配置 |
| `/api/config/full` | GET/POST | 完整配置（读取/更新） |

### 段评下载（重要）

段评通过 `/api/config/full` API 启用，**不要修改 config.yml**（server 不读取它）。

```python
import urllib.request, json

# 1. 启动 server（必须用 --server 参数）
# Start-Process "TomatoNovelDownloader-Win64-v2.4.11.exe" -ArgumentList "--data-dir", $SkillDir, "--server"

# 2. 获取当前配置
with urllib.request.urlopen('http://localhost:18423/api/config/full') as resp:
    config = json.loads(resp.read().decode('utf-8'))

# 3. 启用段评
config['enable_segment_comments'] = True
config['segment_comments_top_n'] = 100

# 4. 保存配置
data = json.dumps(config).encode('utf-8')
req = urllib.request.Request('http://localhost:18423/api/config/full', data=data, headers={'Content-Type': 'application/json'})
urllib.request.urlopen(req)

# 5. 创建下载任务
data = json.dumps({'book_id': 'xxx', 'range_start': 1, 'range_end': 10}).encode('utf-8')
req = urllib.request.Request('http://localhost:18423/api/jobs', data=data, headers={'Content-Type': 'application/json'})
urllib.request.urlopen(req)
```

**段评数据位置**：下载完成后，段评数据在 `downloads/{book_id}/downloaded_chapters.jsonl` 的 `segment_comments` 字段中。

## config.yml 关键配置

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| `novel_format` | 输出格式 | `txt`（蒸馏必须） |
| `enable_segment_comments` | 段评下载 | 通过 API 启用，不要改 config.yml |
| `max_workers` | 并发线程数 | `1` |
| `auto_open_downloaded_files` | 自动打开 | `false` |
