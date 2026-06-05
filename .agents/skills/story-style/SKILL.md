---
name: story-style
description: |
  源文风格分析：拆章+风格指纹+inkos 8维度风格指南。
  输出 style_profile_N.json + style_guide_N.md。
  触发条件：「分析风格」「跑风格分析」「提取风格指南」。
  可与 phase0-strategy 并行运行。
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
python ${CLAUDE_SKILL_DIR}/tools/source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{源书名}/源文/
```

### 0.2 风格指纹（脚本）
```bash
python ${CLAUDE_SKILL_DIR}/tools/style_analyzer.py novel-download-authors/{作者名}/{源书名}/源文/第N章.txt --json | Out-File -FilePath novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/style_profile_N.json -Encoding utf8
```

### 0.3 风格分析（10 agents × N批，并行）

⚠️ **每个 agent 只分析1章，禁止合并多章。**

Task prompt 见 [prompts/style-analysis-task.md](prompts/style-analysis-task.md)。输出保存到 `style_guide_N.md`。

## 缓存策略

- `style_profile_*.json` + `style_guide_*.md` 齐全 → 跳过
- 抽检3个 style_guide：8维度齐全？≥600字？每维度有例句？
- 不合格 → 重跑该章
- 手动刷新 → 删除 `style_profile_*.json` 和 `style_guide_*.md`
