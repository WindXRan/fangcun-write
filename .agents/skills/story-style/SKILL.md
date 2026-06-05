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

> 源文风格分析，可缓存。

## 输入

源文文件：`novel-download-authors/{作者名}/{源书名}/` 下的 txt 文件

## 输出

```
novel-download-authors/{作者名}/{源书名}/
├── 源文/                          # 拆章后的章节文件
└── 蒸馏/mode-b/
    ├── style_profile_N.json       # 脚本指纹
    └── style_guide_N.md           # inkos 8维度风格指南
```

## 流程

### 0.1 拆章
```bash
python .agents/skills/story-style/tools/source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{源书名}/源文/
```

### 0.2 风格指纹（脚本）
```bash
mkdir -Force novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
python .agents/skills/story-style/tools/style_analyzer.py novel-download-authors/{作者名}/{源书名}/源文/第N章.txt --json | Out-File -FilePath novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/style_profile_N.json -Encoding utf8
```

### 0.3 创建风格指南模板（脚本）
```bash
python .agents/skills/story-style/tools/create_templates.py style <章节数> novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/
```

### 0.4 风格分析（10 agents × N批，并行）

⚠️ **每个 agent 只分析1章，禁止合并多章。**

Task prompt 见 [prompts/style-analysis-task.md](prompts/style-analysis-task.md)。输出保存到 `style_guide_N.md`。

## 缓存策略

- `style_profile_*.json` + `style_guide_*.md` 齐全 → 跳过
- 抽检3个 style_guide：
  - 是否有实际分析内容（不是空模板）？
  - 8维度是否全部填入？
  - 每维度有原文例句？
  - 总字数≥600？
- 空模板 = 未完成，需重新分析
- 不合格 → 重跑该章
- 手动刷新 → 删除 `style_profile_*.json` 和 `style_guide_*.md`
