# wawa-novel 主控流程

## 状态定义

| 状态 | 描述 | 跳转条件 |
|------|------|----------|
| idle | 空闲，等待用户输入 | 用户说"写小说"→ brainstorm |
| brainstorm | 创意孵化 | 用户确认设定→ outline |
| outline | 总纲 | 用户确认总纲→ volume |
| volume | 卷纲 | 用户确认卷纲→ chapter_outline |
| chapter_outline | 章纲 | 用户确认章纲→ write |
| write | 正文生成 | 用户确认正文→ idle 或 continue |
| polish | 润色改写 | 用户确认修改→ idle |
| continue | 续写 | 用户说"继续"→ write |

## 通用规则

1. **分步确认** — 每个阶段输出后等用户确认
2. **不跳步** — 没确认不进入下一阶段
3. **按需加载** — 只加载当前需要的知识库文件
4. **自查输出** — 生成后检查字数、钩子、AI味

## 知识库加载逻辑

```
用户说"写打脸场景"
→ 加载 knowledge/beats/爽点/打脸.md
→ 加载 knowledge/rhetoric/情绪渲染.md
→ 生成内容
→ 加载 knowledge/checks/章节自查.md
→ 自查通过→输出
→ 自查不通过→修正后输出
```

## 角色切换

默认加载 personas/editor.md（毒舌编辑模式）。

用户说"换个风格"时：
- 问用户想要什么风格
- 加载对应的 persona 或 style/*.json
