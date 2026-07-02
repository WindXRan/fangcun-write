---
name: fangcun-write
version: 7.0.0
description: |
  方寸仿写引擎。严格工作流合约，禁止跳过任何步骤。
---

# 方寸工作流合约

**以下规则为硬约束，禁止违反。**

---

## 写第N章：三纲法，缺一不可

```
Step 0: 确定卷位置
  → 查看 正文/卷纲/ 确定第N章属于第几卷
  → 读对应卷的卷纲，了解本章在卷弧线中的位置
  → 如果卷纲不存在 → 先建卷纲，再写章

Step 1: preflight
  → quality_checker.py check --chapter N
  → exit code != 0 时禁止继续

Step 2: 源文章纲提取（不允许手动编写章纲）
  → source-guide-reverse 从源文正文提取结构
  → 输出到源文项目 正文/章纲/第N章.xml

Step 3: 章纲转换（不允许直接使用源文章纲）
  → guide-convert 将源文章纲转换为仿写章纲
  → 输出到仿写项目 正文/章纲/第N章.xml
  → 检查 tool 属性必须为 "guide-convert"

Step 4: 写正文（不允许手动编写正文）
  → write-chapter 按仿写章纲写正文
  → 输出到仿写项目 正文/正文/第N章.xml

Step 5: 审查修复
  → fanxie-review（读者视角审查）
  → fanxie-structural-fix（如结构偏离章纲）
  → fanxie-fix（如技法偏差）

Step 6: 质量门禁
  → quality_checker.py audit project_dir
  → exit code != 0 时阻塞，必须修复到通过

Step 7: 展示前500字+尾200字给用户确认
  → 用户说"可以"才进入下一章
```

## 禁止事项（违反视同违约）

```
❌ 禁止手动编写章纲（必须用 source-guide-reverse）
❌ 禁止直接使用源文章纲（必须用 guide-convert 转换）
❌ 禁止手动编写正文（必须用 write-chapter）
❌ 禁止跳过 quality_checker
❌ 禁止跳过用户确认直接下一章
❌ 禁止在仿写中添加源文没有的背景/情节/人物内心
❌ 禁止缩写或扩写源文的信息释放节奏
🔴 禁止洗稿：同一功能不能用和源文相同的句式/措辞/修辞
   ➜ 源文写"主角投胎了。她刚刚被分娩出来，就奋力睁大了眼睛"
   ➜ 洗稿："仿写主角投胎了。她刚刚被分娩出来，就奋力睁大了眼睛" ❌
   ➜ 仿写："仿写主角努力撑开黏糊糊的眼皮，入目是一室烛光" ✅
   ➜ 功能相同（分娩睁眼+环境），措辞完全不同
```

## 允许事项

```
✅ 角色名/称谓/势力名/地名/时代背景的换皮
✅ 保留源文的情绪弧线和信息释放点（必须一致）
✅ 保留源文的节奏密度（段落数、OS密度、对话比例）
✅ 用不同的语言表达相同的情节功能（这才是仿写）
```

## 质量门禁

```bash
# 写前检查（阻塞）
python quality_checker.py check project_dir --chapter N

# 写后审计（阻塞）
python quality_checker.py audit project_dir
```

`exit code 0` = 通过。`exit code 1` = 阻塞，必须先修复。

---

## 🧠 Agent 智能行为规则（必须遵循）

### 1. 【项目状态感知】每次任务开始前必须扫描

**强制规则**：收到任何写作任务时，第一步必须是扫描项目状态。

```python
# 必须执行的项目状态扫描
def scan_project_state():
    """
    Agent 必须主动执行的项目状态扫描。
    扫描结果用于智能决策上下文参数。
    """
    # 1. 扫描已写章节
    written_chapters = scan_directory("正文/正文/*.xml")
    # 2. 扫描章纲
    guides = scan_directory("正文/章纲/*.xml")
    # 3. 识别章节间隙
    gaps = find_chapter_gaps(written_chapters)
    # 4. 返回项目状态报告
    return {
        "written": written_chapters,
        "guides": guides,
        "gaps": gaps,
        "latest": max(written_chapters) if written_chapters else 0
    }
```

**扫描结果必须用于**：
- 决策 `关联章节号` 和 `后续章节号` 的值
- 判断当前章节是否处于"填充间隙"模式
- 确定需要读取哪些补充信息

---

### 2. 【智能上下文决策】根据章节位置自动传参

**核心逻辑**：Agent 必须根据当前章节号和项目状态，智能决策上下文参数。

#### A. 正常顺序写作（无章节间隙）

```
当前章节 N = 5
已写章节 = [1, 2, 3, 4]

→ 自动设置：
  关联章节号 = 4  # 上一章
  后续章节号 = None  # 无后续章节
  
→ 读取内容：
  @关联章节  → 第4章章尾（800字）
  @关联章纲  → 第4章章纲
  @后续章节  → （不读取）
```

#### B. 填充章节间隙（中间空缺）

```
当前章节 N = 4
已写章节 = [1, 2, 3, 6, 7, 8]  # 4-5 是间隙

→ 自动设置：
  关联章节号 = 3  # 最近的前置章节
  后续章节号 = 6  # 最近的后置章节
  
→ 读取内容：
  @关联章节  → 第3章章尾（必须衔接）
  @后续章节  → 第6章章首（必须避免冲突）
  @关联章纲  → 第3章章纲
  
→ 特别提醒：
  ⚠️ 当前处于"填充间隙"模式
  ⚠️ 必须同时衔接前文（第3章）和后文（第6章）
  ⚠️ 确保剧情连贯，不出现断档或重复
```

#### C. 跳跃式写作（跳过某些章节）

```
当前章节 N = 10
已写章节 = [1, 2, 3, 7, 8, 9]  # 4-6 未写

→ 自动设置：
  关联章节号 = 9  # 最近的前置章节
  后续章节号 = None
  
→ 提醒用户：
  ⚠️ 检测到章节跳跃：第3章之后直接写第7章
  ⚠️ 建议：是否先填充第4-6章？
```

---

### 3. 【参考文档】必须读取相关知识

**强制规则**：Agent 必须根据当前任务，主动读取 `references/` 目录下的相关参考文档。

#### 📚 参考文档清单

```
references/
├── 角色与人物
│   ├── character-basics.md           # 角色基础
│   ├── character-design-methods.md   # 角色设计方法
│   ├── character-relations.md        # 角色关系
│   └── cross-book-recall.md         # 跨书召回
│
├── 情感与情绪
│   ├── emotional-arc-design.md      # 情绪弧线设计
│   ├── emotional-methods.md         # 情绪方法
│   └── female-audience-writing.md  # 女频写作
│
├── 题材与类型
│   ├── genre-catalog.md             # 题材目录
│   ├── genre-core-mechanics.md      # 题材核心机制
│   ├── genre-readers.md             # 题材读者
│   └── genre-writing-formulas.md   # 题材写作公式
│
├── 结构与节奏
│   ├── outline-conflict.md          # 大纲冲突
│   ├── outline-methods.md           # 大纲方法
│   ├── outline-rhythm.md            # 大纲节奏
│   ├── outline-structure-theory.md  # 结构理论
│   └── plot-emotion-system.md      # 情节情绪系统
│
├── 开头与钩子
│   ├── opening-design.md            # 开头设计
│   ├── hooks-chapter.md             # 章节钩子
│   ├── hooks-paragraph.md           # 段落钩子
│   └── hooks-suspense.md           # 悬念钩子
│
├── 对话与格式
│   ├── dialogue-mastery.md          # 对话精通
│   └── format-and-structure.md      # 格式与结构
│
├── 核心方法
│   ├── commercial-core-methods.md   # 商业核心方法
│   ├── plot-core-methods.md         # 情节核心方法
│   └── anti-ai-writing.md          # 反AI写作
│
└── 其他
    ├── artifact-protocols.md         # 成品协议
    └── banned-words.md              # 禁用词
```

#### 📖 任务→文档映射

| 当前任务 | 必须读取的文档 |
|---------|---------------|
| 写新章节 | `emotional-arc-design.md`, `hooks-chapter.md`, `outline-rhythm.md` |
| 女频文写作 | `female-audience-writing.md`, `emotional-methods.md` |
| 男频文写作 | `genre-core-mechanics.md`, `plot-core-methods.md` |
| 设计开头 | `opening-design.md`, `hooks-paragraph.md` |
| 创建角色 | `character-basics.md`, `character-design-methods.md` |
| 检查章纲 | `outline-methods.md`, `outline-structure-theory.md` |
| 反AI痕迹 | `anti-ai-writing.md`, `banned-words.md` |

#### 📖 读取规则

```
1. 收到任务后，根据"任务→文档映射"表，确定需要读取的文档
2. 使用 Read 工具读取相关文档
3. 将文档知识应用到当前任务中
4. 如映射表未覆盖，根据任务关键词自行判断相关文档
```

---

### 4. 【自动补充信息】主动提供上下文

**强制规则**：Agent 在调用任何写作工具之前，必须自动附带补充信息。

#### 补充信息模板

```
【当前任务】写第N章

【项目状态】
- 已写章节：X章（第a-b章）
- 本章位置：第N章，属于第X卷
- 章节间隙：有/无（如有，列出具体间隙）

【自动决策的上下文】
- 关联章节号：X（原因：最近的前置章节是X）
- 后续章节号：Y（原因：最近的后置章节是Y，需避免冲突）
- 读取内容：
  ✅ 第X章章尾（800字）→ 用于衔接
  ✅ 第Y章章首（500字）→ 用于避免冲突
  ✅ 第X章章纲 → 用于了解前置剧情

【网文节奏提醒】
- 本章情绪弧线：xxx → xxx → xxx
- 必须出现的爆点：xxx
- 章尾悬念：xxx

【开始执行】
```

---

### 5. 【质量自检】写完后必须自动检查

**强制规则**：每章写完后在展示给用户前，Agent 必须自检：

```
【质量自检清单】

1. 衔接性检查
   - ✅ 章首是否承接上一章结尾情绪？
   - ✅ 是否读了 @关联章节 的章尾？
   - ✅ 前300字是否有"承接句"？

2. 节奏检查
   - ✅ 是否达到章纲规定的情绪弧线？
   - ✅ 信息释放点是否和章纲一致？
   - ✅ 章尾是否有悬念钩子？

3. 版权检查
   - ✅ 是否出现源文角色名？（必须用仿写名）
   - ✅ 是否有和源文相同的句式/措辞？
   - ✅ 是否保留了源文节奏但换了表达？

4. 网文规律检查
   - ✅ 女频：是否有情绪爆点？关系是否有变化？
   - ✅ 男频：主角是否主动？是否有进展？
   - ✅ 通用：对话占比是否合理？OS密度是否合理？

如任何一项 ❌ → 禁止展示给用户，先修复
```

---

### 6. 【用户交互】智能展示和确认

**强制规则**：展示章节给用户时，必须附带智能分析。

```
【展示模板】

第N章已完成，请您审阅：

📖 章节信息
- 章节号：第N章
- 字数：xxxx字
- 情绪弧线：xxx → xxx → xxx
- 核心事件：xxx

✅ 质量自检
- 衔接性：✅ 已承接第X章结尾
- 节奏：✅ 符合章纲要求
- 版权：✅ 无源文残留
- 网文规律：✅ 符合xxx文节奏

📝 前500字
（展示前500字）

📝 尾200字
（展示尾200字）

💡 Agent建议
- 本章xxx处处理优秀
- 建议注意xxx
- 是否继续下一章？

[用户输入：可以 / 需要修改 / ...]
```

---

## 参考：工具清单

| 工具 | 必用？ | 触发条件 |
|------|:------:|---------|
| source-guide-reverse | ✅ 必用 | 每章一次，读源文出章纲 |
| guide-convert | ✅ 必用 | 每章一次，源文章纲→仿写章纲 |
| write-chapter | ✅ 必用 | 有仿写章纲后写正文 |
| quality_checker.py | ✅ 必用 | 写前+写后两次 |
| fanxie-review | ✅ 必用 | 写完后审查 |
| fanxie-structural-fix | ⚠️ 需要时 | 结构偏离章纲时 |
| fanxie-fix | ⚠️ 需要时 | 技法偏差时 |
| character-split | ⚠️ 需要时 | 存在复合角色时 |
| 开书脑洞/开书评估 | 📋 开书阶段 | 新项目启动时 |
| world-mapper | 📋 开书阶段 | 开书评估通过后 |

---

## 🚀 快速启动检查清单

**每次开始工作前，Agent 必须确认**：

- [ ] 是否已扫描项目状态（已写章节、章纲、间隙）？
- [ ] 是否已智能决策上下文参数（关联章节号、后续章节号）？
- [ ] 是否已读取必要的补充信息（关联章节、后续章节、关联章纲）？
- [ ] 是否理解本章在网文节奏中的位置？
- [ ] 是否准备好质量自检清单？

**如任何一项 ❌ → 先完成再开始写作**
