---
name: browser-cdp
description: |
  Use this skill when you need to control a Chrome browser via CDP to reuse existing login sessions.
  触发方式：browser automation, CDP, 浏览器操作, Chrome CDP, 复用登录态, extract token from browser
---

# Browser CDP 操作工具

通过 CDP 协议控制 Chrome，复用已有登录态，执行浏览器自动化操作。

## 前置条件

- macOS / Linux / Windows，已安装 Google Chrome
- Node.js 12+
- `agent-browser` 已安装：`npm install -g agent-browser`

> ⚠️ **首次启动会 kill 用户的常规 Chrome。** 启动前必须征求用户同意。

---

## 启动流程

### 第一步：探测当前状态

```bash
node {SKILL_DIR}/scripts/setup-cdp-chrome.js 9222 --detect-only
```

输出：
- `CDP_STATUS=ready` → 已就绪，可直接复用
- `CDP_STATUS=needs-setup` → 需要启动

### 第二步：根据探测结果分支

- `CDP_STATUS=ready` → 直接使用 `agent-browser --cdp 9222 ...`
- `CDP_STATUS=needs-setup` 且 `CHROME_RUNNING=no` → 安全启动
- `CDP_STATUS=needs-setup` 且 `CHROME_RUNNING=yes` → 先问用户

---

## 常用操作

### 打开页面并等待加载

```bash
agent-browser --cdp 9222 open "<URL>"
agent-browser --cdp 9222 wait 3000
```

### 提取页面文本

```bash
agent-browser --cdp 9222 eval 'document.body.innerText.substring(0, 8000)'
```

### 提取 Auth Token

```bash
agent-browser --cdp 9222 eval 'localStorage.getItem("token") || document.cookie'
```

### 复杂 JS（含引号 / `$` / 反引号）

```bash
# 1) base64 包裹
agent-browser --cdp 9222 eval -b "$(echo -n "document.querySelectorAll('a').length" | base64)"

# 2) heredoc + --stdin
cat <<'EOF' | agent-browser --cdp 9222 eval --stdin
const links = document.querySelectorAll('a');
links.length;
EOF
```

### 页面交互（snapshot 拿元素引用）

```bash
agent-browser --cdp 9222 snapshot -i        # 仅交互元素
agent-browser --cdp 9222 click "<CSS or @e1>"
agent-browser --cdp 9222 type "<sel>" "<text>"
```

---

## 停止 / 清理

- 关掉 debug Chrome 窗口即可
- 登录态失效：`node {SKILL_DIR}/scripts/setup-cdp-chrome.js 9222 --reset --yes`

---

## 超时包装（OpenCode 环境）

Windows：
```powershell
$job = Start-Job { agent-browser --cdp 9222 eval "window.location.replace('https://www.qidian.com/rank/')" }
Wait-Job $job -Timeout 30 | Out-Null
if ($job.State -eq 'Running') { Stop-Job $job; Write-Output "⏱ CDP 操作超时（30s）" }
else { Receive-Job $job }
Remove-Job $job -Force
```

macOS / Linux：
```bash
timeout 30 agent-browser --cdp 9222 eval "window.location.replace('https://www.qidian.com/rank/')"
```

---

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| `NEEDS_CONSENT` + 退出码 3 | 询问用户是否允许杀掉 Chrome，同意后加 `--yes` 重跑 |
| CDP 端口未监听 | `--detect-only` 再确认 |
| 页面跳转到登录页 | `snapshot -i` 找登录按钮并操作 |
| `eval` 返回 `null` | 检查 localStorage key 名 |
| 登录态过期 | `setup-cdp-chrome.js 9222 --reset --yes` |
