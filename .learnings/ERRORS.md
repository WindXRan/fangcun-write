# Errors

Command failures and integration errors.

---

## [ERR-20260601-001] powershell_chinese_encoding

**Logged**: 2026-06-01T12:27:00Z
**Priority**: high
**Status**: pending
**Area**: config

### Summary
PowerShell 5.1 默认使用 GBK 编码，处理中文文件名/内容时会乱码，导致 Python 脚本无法正常执行。

### Error
```
Python -c "..." 输出中文时显示乱码
grep 搜索中文内容失败
文件名显示为乱码
```

### Context
- PowerShell 5.1 默认编码：GBK/cp936
- 项目包含大量中文文件名和内容
- Python 脚本需要 UTF-8 编码

### Suggested Fix
```powershell
# 方案1：设置 PowerShell 编码
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 方案2：使用 Python 替代 PowerShell
python -c "import re; ..."

# 方案3：使用 grep 工具替代 Select-String
grep -r "pattern" path/
```

### Metadata
- Reproducible: yes
- Related Files: skills/story-rewrite/SKILL.md
- Tags: powershell, encoding, chinese, utf-8

---
