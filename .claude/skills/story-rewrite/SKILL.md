---
name: story-rewrite
description: |
  仿写引擎：源文分析 → 文风蒸馏 → 结构映射 → 写章 → 去AI
trigger:
  - /story-rewrite
  - /仿写
  - 继续仿写
  - 写第.*章
  - 继续写
---

# story-rewrite：仿写引擎

## Phase 1：初始化

### 1.0 拆章 + 统计指纹

```bash
# 源文拆章（缓存存在则跳过）
python source_chapter_splitter.py split <源文.txt> novel-download-authors/{作者名}/{书名}/

# 统计指纹（缓存存在则跳过）
python style_analyzer.py <源文.txt> --name "源文全书"
```

### 1.1 新书概念 → `{书名}/设定/新书概念.md`

必含项：
- 书名、类型、核心卖点
- 人物设定（主角+配角）
- **NPC命名映射表**（⚠️ 必填）
- 故事弧线、关键转折点、差异化

NPC映射表格式：
```
| 源文 | 新书 | 身份 |
|---|---|---|
| 楚靳寒 | 顾西洲 | 男主 |
| 宴金集团 | 盛恒集团 | 男主家族企业 |
| ... | ... | ... |
```

规则：源文所有有名有姓的NPC、组织名、地名必须换名。

### 1.2 世界观 → `{书名}/设定/story_bible.md`

世界规则、角色设定、地点设定、关键道具。

### 1.3 真相文件 → `{书名}/真相文件/`

```
current_state.md        # 当前状态
pending_hooks.md        # 伏笔池
chapter_summaries.md    # 章节摘要
character_matrix.md     # 角色关系矩阵
emotional_arcs.md       # 情绪弧线
```

初始化填框架，Phase 2 逐步填充。

---

## Phase 2：写作（每区间10章循环）

### 入口（新开/继续统一执行）

```
Step 0：检查进度
  → ls {书名}/正文/ → 已完成第1~N章
  → 下一区间 = (N+1) ~ (N+10)

Step 1：验证文件存在
  [1] 章纲 ← {书名}/大纲/章纲_{start}-{end}.md
  [2] 蒸馏 ← novel-download-authors/{作者名}/{书名}/蒸馏_{start}-{end}.md
  [3] 真相文件 ← {书名}/真相文件/*.md
  → 缺失则先执行2.1/2.2创建

Step 2：执行2.3写章
Step 3：执行2.4去AI
Step 4：执行2.5更新真相文件
```

禁止：读取源文章节原文、跳过验证直接写章

---

### 2.1 分析（缓存存在则跳过）

```bash
# 逐章分析
python source_chapter_splitter.py extract novel-download-authors/{作者名}/{书名}/ <start> <end> <{书名}/源文_{x-y}.txt>
# 用 prompts/chapter-analyzer.md 分析 → 源文分析_{x-y}.md

# 蒸馏
python style_analyzer.py {书名}/源文_{x-y}.txt
# 用 prompts/style-analysis.md 做8维度分析 → 蒸馏_{x-y}.md
```

### 2.2 章纲 → `{书名}/大纲/章纲_{x-y}.md`

模板：
```markdown
## 第N章 [章名]
- 源文对应：源文第M章 [源文章名]
- 核心事件：[原创事件]
- 情绪弧线：[情绪流动]
- 钩子：[章末钩子]
- 场景：[必须换]
- NPC：[必须用新书名称]
```

### 2.3 写章（3步强制管线）

**Step 1：验证文件**
```
[1] 章纲存在
[2] 蒸馏存在
[3] 真相文件存在
→ 3项全过才继续
```

**Step 2：Task写章**
```
Task(
    description="写第N章",
    subagent_type="general",
    prompt="""
你是一个专业的网文写手。请写出《{书名}》第N章正文。

【章纲】请读取：{书名}/大纲/章纲_{x-y}.md 中第N章
【文风指南】请读取：novel-download-authors/{作者名}/{书名}/蒸馏_{x-y}.md
【真相文件】请读取：{书名}/真相文件/ 下所有 .md 文件

【规则】
1. 只保留源章行文结构，具体内容全部原创
2. 利益冲突/动作/反应全部更换
3. 文风以蒸馏为准
4. 纯正文输出
5. 2000-2500字，硬上限3000字

【输出】保存到：{书名}/正文/第N章.txt
"""
)
```

**Step 3：验证**
```bash
python word_counter.py {书名}/正文/第N章.txt
grep -n "楚靳寒\|宋云绯\|宴金集团\|海市\|青城\|柏庾\|李哲\|李妙\|胡瑶\|何总" {书名}/正文/第N章.txt
```

### 2.4 去AI（每10章）

用 `prompts/de-ai-system.md` 检测→改写→重检测循环。

### 2.5 更新真相文件

更新：current_state / pending_hooks / chapter_summaries / character_matrix / emotional_arcs

---

## Phase 3：收尾

### 3.1 一致性终检

- NPC名称grep（源文原名残留）
- 角色一致性
- 世界观一致性
- 时间线一致性
- 伏笔回收

### 3.2 导出

```bash
cat {书名}/正文/*.txt > {书名}/{书名}.txt
```

---

## 附属文件

| 文件 | 用途 |
|------|------|
| `source_chapter_splitter.py` | 拆章 |
| `style_analyzer.py` | 统计指纹 |
| `word_counter.py` | 字数统计 |
| `prompts/chapter-analyzer.md` | 章节分析 |
| `prompts/style-analysis.md` | 8维度文风分析 |
| `prompts/de-ai-system.md` | 去AI |

## 常见错误

| 错误 | 正确 |
|------|------|
| 不建NPC映射表 | Phase 1必须建 |
| 只换主角名 | 所有NPC/组织/地名都换 |
| 读源文章节原文 | 只读分析+蒸馏+真相文件 |
| 跳过验证直接写章 | 必须验证3文件存在 |
| 蒸馏用全书指标 | 用本区间10章指标 |
| 章纲照搬源文情节 | 只套结构，换内容 |
