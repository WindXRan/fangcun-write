---
name: novel-download
description: |
  小说下载工具。通过 TomatoNovelDownloader server 模式 + 浏览器自动化下载番茄小说，按作者名自动归档到 novel-download-authors/ 目录。
  触发方式：/novel-download、/下载小说、「下载这本小说」「帮我下载XX」
---

# novel-download · 小说下载归档

## 功能

1. **下载小说**：通过 TomatoNovelDownloader server 模式 + 浏览器自动化
2. **按作者归档**：下载到 downloads/ → 归档到 `novel-download-authors/{作者名}/`
3. **批量下载**：支持按作者名搜索并批量下载全部作品

## 文件位置

```
skills/novel-download/
├── TomatoNovelDownloader-Win64-v2.4.11.exe
├── config.yml
├── downloads/          ← 下载临时目录
│   └── {作者名}/       ← 按作者名自动归档
├── scripts/
│   └── archive_novel.py
└── SKILL.md
```

## 数据流

```
番茄小说 → 下载到 downloads/{作者名}/ → 归档到 novel-download-authors/{作者名}/
```

## 文件位置

```
.claude/skills/novel-download/
├── TomatoNovelDownloader-Win64-v2.4.11.exe
├── config.yml
├── downloads/                ← 下载临时目录
├── novel-download-authors/   ← 归档目录
│   └── {作者名}/
│       └── {书名}.txt
├── scripts/
│   └── archive_novel.py
└── SKILL.md
```
番茄小说 → 下载到 downloads/{作者名}/ → 归档到 novel-download-authors/{作者名}/
```

## 文件位置

```
.claude/skills/novel-download/
├── TomatoNovelDownloader-Win64-v2.4.11.exe
├── config.yml
├── downloads/                ← 下载临时目录
├── novel-download-authors/   ← 归档目录
│   └── {作者名}/
│       └── {书名}.txt
├── scripts/
│   └── archive_novel.py
└── SKILL.md
```
番茄小说 → 下载到 downloads/{作者名}/ → 归档到项目 authors/{作者名}/
```

## 使用方式（Server 模式 + 浏览器自动化）

### 全自动流程

1. **启动 server**：
   ```powershell
   Start-Process -FilePath "skills/novel-download/TomatoNovelDownloader-Win64-v2.4.11.exe" `
     -ArgumentList "--data-dir","skills/novel-download","--server" `
     -WorkingDirectory "skills/novel-download" -WindowStyle Hidden
   ```
   服务器默认监听 `http://127.0.0.1:<随机端口>/`，启动后输出端口。

2. **启动 CDP Chrome**：
   ```bash
   node {browser-cdp-skill}/scripts/setup-cdp-chrome.js 9222
   ```

3. **浏览器自动化操作**：
   ```
   agent-browser --cdp 9222 open "http://127.0.0.1:<端口>/"
   agent-browser --cdp 9222 click "<搜索/下载链接>"
   agent-browser --cdp 9222 type "<搜索框>" "<关键词>"
   agent-browser --cdp 9222 click "<搜索按钮>"
   # 找到目标书的下载按钮 → 点击
   # 弹出确认对话框 → 点击"确认下载"
   # 重复直到所有书提交
   ```

4. **查看任务状态**：
   - 点击"任务"链接查看下载进度
   - 等待所有任务显示"完成"

5. **归档**：
   下载完成后文件在 `skills/novel-download/downloads/{作者名}/`。
   移动到 `skills/novel-download/novel-download-authors/{作者名}/`：
   ```powershell
   Move-Item -Path "skills/novel-download/downloads/<作者名>/*" -Destination "skills/novel-download/novel-download-authors/<作者名>/" -Force
   ```

6. **清理**：
   关闭 server 进程和 CDP Chrome。

### API 搜索（备选）

Server 模式提供 REST API：
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:<端口>/api/search?q=<关键词>" -UseBasicParsing
```
返回 JSON，包含 book_id、title、author 等字段。

### 更新已有小说

```powershell
skills/novel-download/TomatoNovelDownloader-Win64-v2.4.11.exe --update <book_id>
```

## config.yml 关键配置

| 配置项 | 说明 |
|--------|------|
| `save_path` | 下载保存路径（指向 downloads/） |
| `novel_format` | 输出格式（必须设为 txt，蒸馏需要 txt 原始文本，不要用 epub） |
| `enable_segment_comments` | 段评下载（建议关闭，触发IP风控） |
| `max_workers` | 并发线程数 |

## 注意事项

- config.yml 必须是合法 UTF-8 YAML，否则 server 启动失败
- 段评建议关闭（`enable_segment_comments: false`），触发IP风控
- 下载完成后关闭 server 进程和 CDP Chrome
- `save_path` 路径中的中文字符需确保 UTF-8 编码正确
