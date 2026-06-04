---
name: story-rewrite
description: |
  仿写引擎：源文分析 → 文风蒸馏 → 结构映射 → 写章 → 去AI
  使用脚本保证一致性，SKILL.md提供上下文。
trigger:
  - /story-rewrite
  - /仿写
  - 继续仿写
  - 写第.*章
  - 继续写
---

# story-rewrite：仿写引擎（2.0版）

## 仿写合规标准

**三条标准**：
1. **人类主导**：人决定写什么，AI只是工具
2. **实质修改**：不能只换名字，要改事件、改因果、改逻辑
3. **无实质性相似**：读者看不出"这和XX书一模一样"

**硬规则**：
- 必须原创事件、因果逻辑、人物关系
- 不能照搬源文的剧情线、反转套路、场景设计

**判断标准**：
- ❌ 读者能猜出"这和XX书一模一样"→失败
- ✅ 只觉得"有类似爽感"→成功

---

## 文件结构

```
novel-download-authors/{作者名}/{书名}/
├── 源文/                    # 源文章节
│   ├── 第1章.txt
│   ├── 第2章.txt
│   └── ...
├── 蒸馏/
│   ├── mode-a/             # Mode A：10章一次蒸馏
│   │   ├── 蒸馏_1-10.md
│   │   ├── 蒸馏_11-20.md
│   │   └── ...
│   └── mode-b/             # Mode B：每章一次蒸馏
│       ├── 蒸馏_1.md
│       ├── 蒸馏_2.md
│       └── ...
├── 源文分析/                # 源文分析（Mode A用）
│   ├── 源文分析_1-10.md
│   ├── 源文分析_11-20.md
│   └── ...
└── _index.txt              # 索引文件

{书名}/
├── 设定/
│   ├── 新书概念.md
│   └── story_bible.md
├── 真相文件/                # Mode A 专用
│   ├── current_state.md
│   ├── pending_hooks.md
│   ├── chapter_summaries.md
│   ├── character_matrix.md
│   └── emotional_arcs.md
├── 大纲/                    # Mode A + B 通用，章纲即真相
│   ├── 章纲_1-10.md        # Mode A
│   └── 章纲_N.md           # Mode B（每章独立）
├── 正文/
│   ├── 第1章.txt
│   └── ...
└── {书名}.txt              # 最终导出
```

---

## Phase 1：初始化

### 1.0 拆章

```bash
python .claude/skills/story-rewrite/tools/source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{书名}/源文/
```

### 1.1 新书概念 → `{书名}/设定/新书概念.md`

必含项：
- 书名、类型、核心卖点
- 人物设定（主角+配角）
- **NPC命名映射表**（⚠️ 必填）
- 故事弧线、关键转折点、差异化

### 1.2 世界观 → `{书名}/设定/story_bible.md`

### 1.3 真相文件 → `{书名}/真相文件/`

```
current_state.md        # 当前状态
pending_hooks.md        # 伏笔池
chapter_summaries.md    # 章节摘要
character_matrix.md     # 角色关系矩阵
emotional_arcs.md       # 情绪弧线
```

---

## Phase 2：写作（两种模式）

### 模式选择

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **Mode A：滑动窗口** | 10章一循环，串行：分析→章纲→写章 | 需要精细控制、手动干预 |
| **Mode B：并行Agent** | 10个agent并行，每个agent独立：蒸馏→章纲→写章 | 一键完成、批量生产 |

---

### Mode A：滑动窗口（10章循环）

#### 入口

```
Step 0：检查进度 → ls {书名}/正文/
Step 1：验证文件 → python scripts/validate_files.py {书名} {章号}
Step 2：执行2.3写章
Step 3：执行2.4去AI
Step 4：执行2.5更新真相文件
```

#### A1 拆章 + 风格分析

```bash
# 1. 拆章
python .claude/skills/story-rewrite/tools/source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{书名}/源文/
python .claude/skills/story-rewrite/tools/source_chapter_splitter.py extract novel-download-authors/{作者名}/{书名}/源文/ <start> <end> <{书名}/源文_{x-y}.txt

# 2. 脚本先行：每章提取统计指纹（不耗token）
for i in range(start, end+1):
    python .claude/skills/story-rewrite/tools/style_analyzer.py novel-download-authors/{作者名}/{书名}/源文/第{i}章.txt --output novel-download-authors/{作者名}/{书名}/蒸馏/mode-a/style_profile_{i}.json

# 3. LLM后行：每10章生成风格指南
# 读取style_profile_{x-y}.json，调用LLM生成风格指南，保存到 novel-download-authors/{作者名}/{书名}/蒸馏/mode-a/style_guide_{x-y}.md
```

**风格分析提示词**：见 `prompts/style-analysis.md`

#### A2 章纲 → `{书名}/大纲/章纲_{x-y}.md`

**章纲格式**（详细版，Mode A专用）：

```markdown
## 第N章 [章名]
- 源文对应：源文第M章 [源文章名]
- 源文事件：[源文发生了什么]（参考）
- 新书事件：[与源文完全不同的事件]（原创）
- 因果逻辑：[详细因果链，如：女主不查岗 → 男主好奇 → 约商场 → 抽奖 → 电动车回家]
- 情绪弧线：[情绪流动]
- 钩子：[章末钩子]
```

**风格分析**（脚本+LLM）：
- 脚本：style_profile_N.json（统计指纹）
- LLM：style_guide_N.md（8个维度）

#### A3 写章（3步强制管线）

**Step 1：验证文件（脚本保证一致性）**
```bash
python scripts/validate_files.py {书名} {章号}
```

**Step 2：并行启动所有章节**
```
⚠️ 禁止主agent直接写正文！必须用Task工具！
⚠️ 写10章时，必须在一个消息里同时启动10个Task！

每个Task的prompt：
"""
你是一个专业的网文写手。请写出《{书名}》第N章正文。

【章纲】请读取：{书名}/大纲/章纲_{x-y}.md 中第N章
【文风指南】请读取：novel-download-authors/{作者名}/{书名}/蒸馏/mode-a/style_guide_{x-y}.md
【风格指纹】请读取：novel-download-authors/{作者名}/{书名}/蒸馏/mode-a/style_profile_N.json
【真相文件】请读取：{书名}/真相文件/ 下所有 .md 文件

【合规仿写规则】
- 可以借鉴：爽点公式、宏观框架、节奏结构
- 必须原创：人设细节、具体事件、因果逻辑链
- 判断标准：读者能猜出"这和XX书一模一样"→失败；只觉得"有类似爽感"→成功

【输出】保存到：{书名}/正文/第N章.txt
"""
```

**Step 3：字数统计**
```bash
python .claude/skills/story-rewrite/tools/word_count.py {书名}/正文/第N章.txt
```

#### A4 更新真相文件（脚本保证一致性）

```bash
python scripts/update_truth_files.py {书名} {章号} "{章名}" "{摘要}" "{事件1}|{事件2}|{事件3}"
```

---

### Mode B：并行Agent（三轮子agent）

> Mode B 不使用真相文件，章纲就是唯一真相。续写时读前面的章纲即可接上。

#### 流程概览

```
输入：源文.txt
    ↓
拆章 + 脚本风格指纹（B1）
    ↓
第一轮：10个子agent做风格分析（B2）→ 产出 style_guide_N.md
    ↓
第二轮：10个子agent做章纲（B3）→ 产出 章纲_N.md
    ↓
第三轮：10个子agent写章（B4）→ 产出 第N章.txt
    ↓
循环（下一批10章）
```

#### B1 拆章 + 脚本风格指纹

```bash
# 1. 拆章
python .claude/skills/story-rewrite/tools/source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{书名}/源文/

# 2. 脚本先行：每章提取统计指纹（不耗token）
for i in range(start, end+1):
    python .claude/skills/story-rewrite/tools/style_analyzer.py novel-download-authors/{作者名}/{书名}/源文/第{i}章.txt --output novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_profile_{i}.json
```

#### B2 第一轮：风格分析（并行10个子agent）

```
⚠️ 禁止主agent直接分析！必须用Task工具！
⚠️ 必须在一个消息里同时启动10个Task！

每个Task的prompt：
"""
你是一个专业的文风分析师。请分析《{书名}》第N章的写作风格。

【源文】请读取：novel-download-authors/{作者名}/{书名}/源文/第N章.txt
【风格指纹】请读取：novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_profile_N.json

【任务】
结合源文和风格指纹，生成风格指南（8个维度）：
1. 句式特征 2. 对话风格 3. 描写手法 4. 节奏特点
5. 情绪表达 6. 用词偏好 7. 段落结构 8. 叙事视角

【输出】保存到：novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_guide_N.md
"""
```

**风格分析提示词**：见 `prompts/style-analysis.md`

#### B3 第二轮：章纲生成（并行10个子agent）

```
⚠️ 风格分析完成后才启动本轮！

每个Task的prompt：
"""
你是一个专业的网文大纲师。请为《{书名}》第N章生成章纲。

【源文】请读取：novel-download-authors/{作者名}/{书名}/源文/第N章.txt（仅参考，不能照搬）
【风格指南】请读取：novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_guide_N.md
【新书概念】请读取：{书名}/设定/新书概念.md
【前序章纲】请读取：{书名}/大纲/ 下已有的章纲文件（如有），了解前文剧情

【章纲格式（Mode B简化版）】
## 第N章 [章名]
- 源文对应：源文第M章 [源文章名]
- 新书事件：[与源文完全不同的事件]（原创）
- 因果逻辑：[详细因果链]
- 情绪弧线：[情绪流动]
- 钩子：[章末钩子]

【合规仿写规则】
- 可以借鉴：爽点公式、宏观框架、节奏结构
- 必须原创：人设细节、具体事件、因果逻辑链
- 判断标准：读者能猜出"这和XX书一模一样"→失败；只觉得"有类似爽感"→成功

【输出】保存到：{书名}/大纲/章纲_N.md
"""
```

#### B4 第三轮：写章（并行10个子agent）

```
⚠️ 章纲完成后才启动本轮！
⚠️ 写10章时，必须在一个消息里同时启动10个Task！

每个Task的prompt：
"""
你是一个专业的网文写手。请写出《{书名}》第N章正文。

【章纲】请读取：{书名}/大纲/章纲_N.md
【风格指南】请读取：novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_guide_N.md
【风格指纹】请读取：novel-download-authors/{作者名}/{书名}/蒸馏/mode-b/style_profile_N.json

【合规仿写规则】
- 可以借鉴：爽点公式、宏观框架、节奏结构
- 必须原创：人设细节、具体事件、因果逻辑链
- 判断标准：读者能猜出"这和XX书一模一样"→失败；只觉得"有类似爽感"→成功

【写完后】用脚本统计字数：
python .claude/skills/story-rewrite/tools/word_count.py {书名}/正文/第N章.txt

【输出】保存到：{书名}/正文/第N章.txt
"""
```

#### B5 循环

```
检查是否还有未写章节：
- 有 → 回到B1，启动下一批10章
- 无 → 结束
```

---

## Phase 3：收尾

### 3.1 一致性终检

```bash
grep -n "源文原名1\|源文原名2" {书名}/正文/*.txt
```

### 3.2 导出

```bash
cat {书名}/正文/*.txt > {书名}/{书名}.txt
```

---

## 仿写风险自测表（写完必查）

写完任何一段内容后，对照这个表检查：

1. 我是不是只参考了一本书？
2. 我的主角是不是和某本爆款书的主角性格、背景、目标几乎一样？
3. 我的剧情是不是可以用"把原书的人物名字换成我的"来描述？
4. 我的剧情因果链是不是和原书完全一样？
5. 连续3章的剧情节点是不是和原书完全对应？
6. 有没有读者看完后说"这和XX书一模一样"？

**只要有任何一个"是"，就立刻修改。**

---

## 脚本说明

| 脚本 | 用途 | 位置 |
|------|------|------|
| `source_chapter_splitter.py` | 拆分源文章节 | `tools/` |
| `style_analyzer.py` | 提取风格统计指纹 | `tools/` |
| `scripts/validate_files.py` | 验证文件是否存在 | `scripts/` |
| `scripts/update_truth_files.py` | 更新真相文件 | `scripts/` |
| `tools/word_count.py` | 统计字数 | `tools/` |

---

## 详细文档

- 章节分析：`prompts/chapter-analyzer.md`
- 文风分析：`prompts/style-analysis.md`
- 真相文件：`truth-files.md`
