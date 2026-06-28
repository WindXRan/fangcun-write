# 管线目录

每个管线定义一组按顺序执行的工具调用，完成一个独立的工作阶段。

## 管线一览

| 管线 | 阶段 | 工具 | 用途 |
|------|------|------|------|
| [reverse-engineer](reverse-engineer.md) | 逆向拆书 | character-extract → book-import → skeleton → style-analysis → adaptation | 把源书拆成结构化数据 |
| [outline-build](outline-build.md) | 仿写搭建 | open-book → volume-outline → plot-guide | 从逆向结果生成新书框架 |
| [chapter-write](chapter-write.md) | 正文写作 | write-chapter → deslop → compare（每章循环） | 按章纲写正文并审查 |
| [quality-check](quality-check.md) | 质量审查 | compare + deslop + 人工确认 | 独立的质量门禁 |

## 调用方式

每个管线是 markdown 文档，**不是可执行脚本**。AI 读管线文档然后依次调 `run_tool()`。

```python
# 例如执行逆向拆管线第1步：
from tool_executor import run_tool
run_tool("character-extract", {"workers": 5}, "/path/to/project")
```

## 阶段总图

```
reverse-engineer → outline-build → chapter-write (循环)
                                         ↓
                                   quality-check (循环)
```
