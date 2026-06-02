# Skill: story-author-query

# 作者作品查询工具

## 功能

查询番茄小说作者的作品列表、粉丝数、总字数等信息。

## 触发方式

- `/story-author-query`、`/查作者`
- 「查一下XX有几本书」「XX写了哪些书」「XX的作品列表」

## 使用流程

### 1. 启动服务（如未运行）

```powershell
$skillDir = "C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\.claude\skills\novel-download"
$exe = "$skillDir\TomatoNovelDownloader-Win64-v2.4.11.exe"

# 检查是否已运行
$proc = Get-Process TomatoNovelDownloader -ErrorAction SilentlyContinue
if (!$proc) {
    Start-Process -FilePath $exe -ArgumentList "--data-dir", $skillDir, "--server" `
        -WorkingDirectory $skillDir -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

# 获取端口
netstat -ano | findstr "LISTENING" | findstr "127.0.0.1:18"
```

### 2. 启动 CDP Chrome

```powershell
taskkill /F /IM chrome.exe 2>$null
Start-Sleep -Seconds 2
Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList `
    "--remote-debugging-port=9222", "--user-data-dir=C:\Users\Administrator\chrome-debug-profile", `
    "--no-first-run", "--no-default-browser-check" -WindowStyle Hidden
Start-Sleep -Seconds 5
```

### 3. 查询作者

**重要：每次搜索前必须清空搜索框，否则会累积之前的搜索词！**

```bash
# 打开搜索页面
agent-browser --cdp 9222 open "http://127.0.0.1:{port}/#search"
Start-Sleep -Seconds 2

# 清空搜索框（关键步骤！）
agent-browser --cdp 9222 eval "document.querySelector('input').value = ''; document.querySelector('input').dispatchEvent(new Event('input', { bubbles: true }));"
Start-Sleep -Seconds 1

# 点击输入框聚焦
agent-browser --cdp 9222 click 'input'
Start-Sleep -Seconds 1

# 输入作者名搜索
agent-browser --cdp 9222 type 'input' "{作者名}"
Start-Sleep -Seconds 2

# 按回车搜索
agent-browser --cdp 9222 press "Enter"
Start-Sleep -Seconds 8

# 获取结果快照
agent-browser --cdp 9222 snapshot -i
```

### 4. 解析结果

从快照中提取：
- 书名
- 作者名
- Book ID
- 是否已下载（检查本地目录）

### 5. 对比本地已下载

```powershell
$authorDir = "C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\.claude\skills\novel-download\novel-download-authors\{作者名}"
Get-ChildItem "$authorDir\*.txt" -ErrorAction SilentlyContinue
```

### 批量查询脚本

```powershell
$port = 18423  # 实际端口
$authors = @("作者1", "作者2", "作者3")

foreach ($author in $authors) {
    Write-Host "`n=== $author ==="
    agent-browser --cdp 9222 open "http://127.0.0.1:$port/#search" 2>$null
    Start-Sleep -Seconds 2
    
    # 清空搜索框
    agent-browser --cdp 9222 eval "document.querySelector('input').value = ''; document.querySelector('input').dispatchEvent(new Event('input', { bubbles: true }));" 2>$null
    Start-Sleep -Seconds 1
    
    # 聚焦并输入
    agent-browser --cdp 9222 click 'input' 2>$null
    Start-Sleep -Seconds 1
    agent-browser --cdp 9222 type 'input' $author 2>$null
    Start-Sleep -Seconds 2
    
    # 搜索
    agent-browser --cdp 9222 press "Enter" 2>$null
    Start-Sleep -Seconds 8
    
    # 解析结果
    $snapshot = agent-browser --cdp 9222 snapshot -i 2>&1
    $authorCount = ($snapshot | Select-String "cell `"$author`"" | Measure-Object).Count
    Write-Host "找到 $authorCount 本作品"
}
```

## 输出格式

```
📚 作者：隔胳呜呜
📊 搜索结果：2本可下载

| # | 书名 | Book ID | 本地状态 |
|---|------|---------|----------|
| 1 | 校花学姐从无绯闻，直到我上大学 | 7207072067127086118 | ✅ 已下载 |
| 2 | 我一理工男，竟是清纯校花白月光 | 7551699466571500569 | ✅ 已下载 |

💡 提示：番茄网站显示该作者可能有其他作品，但下载器未收录。
```

## 注意事项

1. **搜索框必须清空**：每次搜索前必须用JS清空搜索框，否则会累积之前的搜索词导致结果错误
2. 下载器搜索API返回的结果可能少于番茄网站实际数量
3. 搜索结果为0时，建议提示用户在番茄网站手动确认
4. 查询完成后及时清理Chrome进程
5. 等待时间：搜索后建议等待8秒，确保结果加载完成

## 关联 Skill

- `novel-download` - 下载小说
- `story-distill` - 蒸馏作者风格
