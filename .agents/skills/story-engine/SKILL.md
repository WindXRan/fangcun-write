---
name: story-engine
description: |
  小说仿写引擎。从源文生成新书：开书设定 → 章纲 → 写章 → 对比审核。
  触发方式：「仿写这本书」「帮我仿写XX」「写第N章」「继续写」「开书」
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(mkdir *) Bash(rm *)
---

# story-engine：小说仿写引擎

## 你是 agent，用户不会记命令。你负责：

1. **理解用户意图**（"仿写这本书" → 跑全流程；"写第5章" → 只跑 write）
2. **组装正确的命令**（读下面的流程说明，拼出 python 命令）
3. **检查输出质量**（读生成的文件，告诉用户结果）
4. **处理错误**（如果命令失败，读错误信息，修复后重跑）

## 项目结构

```
projects/{作者}/{源书名}/
├── _cache/                    ← 源书级产物（自动管理，不用手动操作）
│   ├── chapters/              ← 源文拆章（153个 txt）
│   ├── events.json            ← 事件表
│   ├── story_skeleton.md      ← 故事骨架
│   ├── adaptation_strategy.md ← 改编策略
│   └── styles/                ← 文笔指纹
├── rewrites/{新书名}/         ← 仿写产物（用户关心的）
│   ├── source_analysis.md     ← 源文分析
│   ├── settings/              ← 设定文件
│   │   ├── characters.md      ← 角色设定
│   │   ├── world.md           ← 世界观
│   │   ├── plot.md            ← 剧情设定
│   │   └── book_info.md       ← 书籍信息
│   ├── characters/            ← 角色卡（每个角色独立文件）
│   ├── guides/                ← 章纲（plot_{N}.md + style_{N}.md）
│   ├── chapters/              ← 正文（ch_{N}.txt）
│   ├── compare/               ← 对比报告
│   └── state.json             ← 进度状态
└── configs/{config}.json      ← 配置文件
```

## 流程（按顺序，每步有依赖）

```
source-engine: event → skeleton → adaptation    ← 源书级，只跑一次
story-engine:  open_book → guides → write       ← 仿写级，可反复跑
```

### Step 1: 源书分析（只跑一次，结果缓存在 _cache/）

```bash
python .agents/skills/source-engine/tools/pipeline.py --config {config} --phase event       # 事件提取
python .agents/skills/source-engine/tools/pipeline.py --config {config} --phase skeleton     # 故事骨架
python .agents/skills/source-engine/tools/pipeline.py --config {config} --phase adaptation   # 改编策略
```

产物：`_cache/events.json` + `_cache/story_skeleton.md` + `_cache/adaptation_strategy.md`

### Step 2: 开书（生成设定，只跑一次）

```bash
python .agents/skills/story-engine/tools/pipeline.py --config {config} --phase open_book --skip-confirm
```

产物：`rewrites/{新书名}/settings/` + `rewrites/{新书名}/characters/`

### Step 3: 写章（可反复跑，支持增量）

```bash
python .agents/skills/story-engine/tools/pipeline.py --config {config} --phase write --start {N} --end {M} --skip-confirm
```

产物：`rewrites/{新书名}/chapters/ch_{N}.txt`

### Step 4: 对比审核（可选）

```bash
python .agents/skills/story-engine/tools/pipeline.py --config {config} --phase compare --start {N} --end {M} --skip-confirm
```

产物：`rewrites/{新书名}/compare/`

### 断点续传

```bash
python .agents/skills/story-engine/tools/pipeline.py --config {config} --phase write --skip-confirm
# 自动从 state.json 读取上次进度，跳过已完成章节
```

## 配置文件格式

```json
{
  "book_name": "auto",                    // "auto" = 让 LLM 自动起名
  "author": "作者名",
  "source_book": "源书名",
  "rewrites_dir": "projects/作者/源书名/rewrites/auto",
  "base_dir": ".",
  "api_key": "sk-xxx",                    // 或从 $env:API_KEY 读取
  "api_base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "prompt_overrides": {                   // 可选：覆盖特定 prompt 的模型
    "open-book.md": {"model": "deepseek-chat"},
    "write-chapter.md": {"model": "deepseek-chat"}
  }
}
```

## 质量检查（agent 自动执行）

写完章后，agent 应该：

1. 读 `chapters/ch_{N}.txt`，检查字数是否在 2000-3000
2. 检查是否有源文角色名残留（读 `characters/` 目录，对比源文名）
3. 检查章节衔接（读上一章结尾和本章开头，确认连贯）
4. 如有问题，告诉用户并建议修复方案

## 常见场景

| 用户说 | agent 做 |
|--------|----------|
| "仿写这本书" | 先问配置参数 → 跑全流程 source→open→write |
| "写第5章" | 检查 guides 是否存在 → 跑 write --start 5 --end 5 |
| "继续写" | 读 state.json → 从断点继续 |
| "看看写得怎么样" | 读 chapters/ → 跑 compare → 汇报结果 |
| "改一下第3章" | 删除 ch_003.txt → 重跑 write --start 3 --end 3 |
| "角色名不对" | 修改 characters.md → 重跑受影响的章节 |
