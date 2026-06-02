---
name: novel-download
description: |
  小说下载工具。通过 TomatoNovelDownloader server 模式 + CDP 浏览器自动化下载番茄小说，按作者名自动归档到 novel-download-authors/ 目录。
  触发方式：/novel-download、/下载小说、「下载这本小说」「帮我下载XX」
---

# novel-download · 小说下载归档

## 目录结构

```
.claude/skills/novel-download/
├── TomatoNovelDownloader-Win64-v2.4.11.exe
├── config.yml
├── scripts/
│   ├── archive_novel.py
│   └── download_by_author.ps1
├── downloads/                    # 下载临时目录（带 book_id 子目录）
├── novel-download-authors/       # 归档目录（永久）
│   └── {作者名}/{书名}.txt
└── SKILL.md
```

## 一键下载（推荐）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/download_by_author.ps1 -Author "初点点"
```

## 手动流程

### 1. 启动 server

```powershell
$skillDir = "C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\.claude\skills\novel-download"
# 清理旧进程
Get-Process TomatoNovelDownloader -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1

Start-Process -FilePath "$skillDir\TomatoNovelDownloader-Win64-v2.4.11.exe" `
  -ArgumentList "--data-dir", $skillDir, "--server" `
  -WorkingDirectory $skillDir -WindowStyle Hidden
Start-Sleep -Seconds 5

# 从日志读取端口
$logFile = Get-ChildItem "$skillDir\logs\*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$port = (Get-Content $logFile.FullName -Raw) -match 'listening on.*?(\d{4,5})' | ForEach-Object { $Matches[1] }
```

### 2. 启动 CDP Chrome

```powershell
taskkill /F /IM chrome.exe 2>$null; Start-Sleep -Seconds 2
Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList `
  "--remote-debugging-port=9222", "--user-data-dir=C:\Users\Administrator\chrome-debug-profile", `
  "--no-first-run", "--no-default-browser-check" -WindowStyle Hidden
Start-Sleep -Seconds 5
```

### 3. 搜索

```bash
agent-browser --cdp 9222 open "http://127.0.0.1:{port}/#search"
agent-browser --cdp 9222 type 'input' "初点点"
agent-browser --cdp 9222 press "Enter"
```

### 4. 下载（逐本操作）

**重要：ref 选择器格式是 `@eXX`（不是 `[ref=eXX]`）**

```bash
# 查看搜索结果，找到下载按钮的 ref
agent-browser --cdp 9222 snapshot -i
# 输出示例: button "下载" [ref=e93]

# 点击下载按钮 → 弹出预览弹窗
agent-browser --cdp 9222 click "@e93"
# 如果报 "Missing arguments"，检查是否用了引号: click "@e93"

# 等待预览弹窗出现，找到"确认下载"按钮
agent-browser --cdp 9222 snapshot 2>&1 | grep "确认下载"
# 输出示例: button "确认下载" [ref=e18]

# 点击确认下载
agent-browser --cdp 9222 click "@e18"
```

### 5. 检查任务状态

```powershell
# API 方式（推荐）
$jobs = Invoke-WebRequest "http://127.0.0.1:{port}/api/jobs" -UseBasicParsing
$jobs.Content

# 或浏览器方式
agent-browser --cdp 9222 open "http://127.0.0.1:{port}/#jobs"
agent-browser --cdp 9222 snapshot -i
```

### 6. 归档

下载完成后文件在 `downloads/` 目录（按 book_id 子目录或直接 txt）。

```powershell
$skillDir = "C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\.claude\skills\novel-download"
$authorDir = "$skillDir\novel-download-authors\初点点"
New-Item -ItemType Directory -Path $authorDir -Force | Out-Null

# 移动 txt 文件
Get-ChildItem "$skillDir\downloads\*.txt" | ForEach-Object {
    Move-Item $_.FullName "$authorDir\$($_.Name)" -Force
    Write-Host "归档: $($_.Name)"
}
```

### 7. 复制到 story-style（蒸馏用）

**关键：必须用 UTF-8 无 BOM 写入，否则蒸馏时读取乱码**

```powershell
$author = "初点点"
$srcDir = "$skillDir\novel-download-authors\$author"
$dstDir = "C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\.claude\skills\story-style\$author\sources"
New-Item -ItemType Directory -Path $dstDir -Force | Out-Null

Get-ChildItem "$srcDir\*.txt" | ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName, [System.Text.Encoding]::UTF8)
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText("$dstDir\$($_.Name)", $content, $utf8NoBom)
    Write-Host "复制: $($_.Name)"
}
```

### 8. 清理

```powershell
Get-Process TomatoNovelDownloader -ErrorAction SilentlyContinue | Stop-Process -Force
taskkill /F /IM chrome.exe 2>$null
```

## 编码验证

```powershell
$path = "novel-download-authors/初点点/惊华庭.txt"
$content = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
$head = $content.Substring(0, [Math]::Min(100, $content.Length))
if ($head -match '[锛€浠涔﹀悕鐩綍]') { "编码损坏" } else { "编码正常" }
```

## 已知 bug 和注意事项

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `click "[ref=eXX]"` 失败 | ref 格式错误 | 用 `click "@eXX"` |
| `eval` 报 SyntaxError | JS 中引号/特殊字符冲突 | 简化 JS，避免模板字符串 |
| Chrome 连接断开 | 长时间操作后 Chrome 崩溃 | 重启 Chrome + 重连 |
| story-style/sources/ 乱码 | 复制时编码被破坏 | 用 `UTF8Encoding::new($false)` 写入 |
| 搜索结果不显示 | 页面 hash 变化但内容未刷新 | 用 `press "Enter"` 提交搜索 |

## config.yml 关键配置

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| `novel_format` | 输出格式 | `txt`（蒸馏必须） |
| `enable_segment_comments` | 段评下载 | `false`（防风控） |
| `max_workers` | 并发线程数 | `1` |
| `auto_open_downloaded_files` | 自动打开 | `false` |
