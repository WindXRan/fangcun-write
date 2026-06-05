---
name: story-style
description: |
  源文风格分析：拆章+风格指纹+inkos 8维度风格指南。
  输出 style_profile_N.json + style_guide_N.md。
  触发条件：用户说「分析风格」「跑风格分析」「提取风格指南」，或直接传源文文件路径。
  可与 story-strategy 并行运行。
argument-hint: <源文.txt路径>
allowed-tools: Bash(python *) Bash(ls *) Bash(mkdir *)
shell: powershell
---

# story-style

> 源文风格分析，可缓存。所有工具和prompt引用 story-engine。

## 共享文件

- 工具：`.agents/skills/story-engine/tools/`
- prompt：`.agents/skills/story-engine/prompts/style-analysis-task.md`

## 输出

```
novel-download-authors/{作者名}/{源书名}/
├── 源文/                          # 拆章后章节
└── 蒸馏/mode-b/
    ├── style_profile_N.json       # 脚本指纹
    ├── style_guide_N.md           # inkos 8维度风格指南（模板+填入）
```

## 流程

### 0.1 拆章
```bash
python .agents/skills/story-engine/tools/source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{源书名}/源文/
```

### 0.2 风格指纹（脚本）
```bash
mkdir -Force novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
python .agents/skills/story-engine/tools/style_analyzer.py novel-download-authors/{作者名}/{源书名}/源文/第N章.txt --json | Out-File -FilePath novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/style_profile_N.json -Encoding utf8
```

### 0.3 创建分析模板（脚本）
```bash
python .agents/skills/story-engine/tools/create_templates.py style <章节数> novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
python .agents/skills/story-engine/tools/create_templates.py hook <章节数> novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
```

### 0.4 风格分析 + 钩子分析（10 agents × N批，并行）

⚠️ **每个 agent 只分析1章，禁止合并多章。**

Task prompt 见 `.agents/skills/story-engine/prompts/style-analysis-task.md`（风格）和 `.agents/skills/story-engine/prompts/hook-analysis-task.md`（钩子）。

每个 agent 读1个源文，输出 `style_guide_N.md` + `hook_guide_N.md` 两个文件。

## 缓存策略

- `style_profile_*.json` + `style_guide_*.md` 齐全 → 跳过
- 抽检3个 style_guide：是否有实际分析内容（不是空模板）？8维度全部填入？每维度有原文例句？总字数≥600？
- 空模板 = 未完成，需重新分析
- 手动刷新 → 删除 `style_profile_*.json` 和 `style_guide_*.md`
