---
name: story-recycle
description: |
  项目文件回收站。HOOK 全局拦截 Path.unlink / shutil.rmtree，
  删前自动备份到 projects/{作者}/{书名}/_recycle/，零侵入。
  触发方式：自动生效（import 即装钩），CLI 管理用 python recycle_hook.py
allowed-tools: Bash(python *)
shell: powershell
---

# story-recycle · 项目回收站

## 原理

在 Python 层 patch `Path.unlink`、`shutil.rmtree`：

1. 检测路径是否在 `projects/` 下
2. 是 → `copy2` 到 `_recycle/{timestamp}_{filename}` → 执行原删除
3. 否 → 直接放行

import 一次，全局生效。改一行就能用。

## 用法

### HOOK（自动备份）

```python
# 在脚本入口（rewrite_chapters.py / 任何工具）加上：
from recycle_hook import install_hook
install_hook()
```

之后所有 `file.unlink()`、`shutil.rmtree()` 操作
如果目标在 `projects/` 下，自动进回收站。

### CLI 管理

```bash
# 查看回收站
python .agents/skills/story-recycle/tools/recycle_hook.py --list projects/作者/书名

# 还原文件
python .agents/skills/story-recycle/tools/recycle_hook.py --restore projects/作者/书名/_recycle/20260611_ch_001.txt

# 清空（可选只清超过7天的）
python .agents/skills/story-recycle/tools/recycle_hook.py --empty projects/作者/书名 --days 7

# 统计信息
python .agents/skills/story-recycle/tools/recycle_hook.py --info projects/作者/书名
```

### HOOK 装在哪

推荐在所有 pipeline 入口加。当前主要入口：

| 入口文件 | 加在哪 |
|----------|--------|
| `rewrite_chapters.py` | 文件顶部 import |
| `unified_fixer.py` | 文件顶部 import |
| `unified_reviewer.py` | 文件顶部 import |
| `auto_optimize.py` | 文件顶部 import |

**Agent 启动规则**：每次运行 pipeline 或调工具脚本前，先 import install_hook。

## 回收站结构

```
projects/作者/书名/
└── _recycle/
    ├── 20260611_143022_234_ch_001.txt    # 文件
    └── 20260611_143030_456_compare/       # 目录（rmtree 整目录备份）
```

文件名前缀 `{日期}_{时间}_{微秒}`，防冲突，排序即删除顺序。

## 注意

- **`_recycle/` 路径不触发 hook**，不会死循环
- **备份失败不阻塞删除**，原操作照常执行（防业务中断）
- **跨进程不继承**：subprocess 调别的脚本需要那个进程也 import hook
- **不保护 subprocess shell rm**：OS 级别的删不走 Python 层
