---
name: novel-download
description: |
  小说下载工具。驱动 TomatoNovelDownloader 下载番茄小说，按作者名自动归档到 authors/ 目录。
  触发方式：/novel-download、/下载小说、「下载这本小说」「帮我下载XX」
---

# novel-download · 小说下载归档

## 功能

1. 下载小说：通过 TomatoNovelDownloader 下载番茄小说
2. 按作者归档：自动识别作者，存入 authors/{作者名}/
3. 批量下载：支持从书单批量下载

## 使用方式

### 单本下载

用户提供 book_id 或书名：

1. 运行 TomatoNovelDownloader-Win64-v2.4.11.exe
2. 用户在 TUI 中完成下载
3. 下载完成后，读取文件头部获取作者名
4. 移动到 authors/{作者名}/

### 更新已有小说

TomatoNovelDownloader-Win64-v2.4.11.exe --update <book_id>

## 归档脚本

python .claude/skills/novel-download/scripts/archive_novel.py <下载目录或文件>

## 注意事项

- TomatoNovelDownloader 是 TUI 应用，需要用户交互完成下载
- config.yml 的 save_path 指向临时目录
- 段评建议关闭（触发IP风控）