---
name: story-engine
description: |
   仿写引擎 vPlan：全书规划先行，一次出稿。
   触发条件：用户说「仿写」「用vPlan写」「帮我仿写这本书」「写第N章」「继续写」。
    全书规划（弧线+映射）在写作前完成，写章阶段直出+批后冲突检测。直出模式：写章agent直接读取plot_guide，跳过章纲。
   不要在用户只是问「怎么写小说」「帮我写大纲」时触发。
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(cp *) Bash(mkdir *)
shell: powershell
---

# story-engine

> 全书规划先行，纯写作出稿。

## 文件结构

⚠️ **章节命名格式**：`第N章`（N 为阿拉伯数字），如 `第1章`、`第2章`、`第101章`。

```
novel-download-authors/{作者名}/
├── {源书名}.txt                 # 原文合并文件（开头含书名/分类/标签/简介+全部章节）

蒸馏/mode-b/                     # 分析产物，由story-style生成
├── plot_guide_N.md              # 情节指南（必读）
├── de-ai_guide_N.md             # 去AI指南（含统计指纹，必读）
├── style_guide_N.md             # 风格指南（可选）
├── hook_guide_N.md              # 钩子指南（关闭）
└── character_guide_N.md         # 角色指南（关闭）

仿写/{新书名}/
├── 设定/
│   ├── 新书设定.md（书名+类型+卖点+人设+NPC映射+世界观）
│   ├── 全书弧线.md（情感曲线+角色成长+伏笔+转折点）
│   ├── 简介.md（3种风格）
│   ├── plot_overview.md
│   └── 章节顺序.md
├── 追踪/
│   └── 真相.md（时间线+角色状态+伏笔状态，批后更新）
└── 正文/第N章.txt
```

## 去重等级

默认 Lv1+Lv2。Lv2 触发逻辑标准（至少满足2条）：起因不同、动机不同、后果不同、参与人不同。

---

## Phase 0：源文分析（写章参考，不阻塞开书）

开书不需要plot_guide。开书只需读源文合并文件的开头部分（含书名/分类/标签/简介），就知道是什么故事。
plot_guide 是写章阶段的精细化参考，与开书完全并行。

### 分析模式（读取 analysis-modes.json）

| 模式 | 输出 | 用途 | 默认 |
|------|------|------|------|
| plot | plot_guide_N.md | 情节节奏骨架（写章时用） | 必需 |
| style | style_guide_N.md | 文风仿写指南（可选） | 增强 |
| de-ai | de-ai_guide_N.md | 统计指纹（脚本生成，无LLM，写章必读） | 必需 |
| hook | hook_guide_N.md | 钩子技法指南 | 关闭 |
| character | character_guide_N.md | 角色塑造指南 | 关闭 |

### 流程

1. 检查 `蒸馏/mode-b/` 下已有 guide → 跳过
2. 拆章（已存在则跳过）
3. 创建蒸馏模板：`python create_templates.py all <章节数> <输出目录>`
4. 流式分批（与开书并行，不阻塞）：
   - plot：10 agents 并行（优先）
   - de-ai：plot 全部完成后启动，10 agents 并行
   - style：plot 全部完成后启动，10 agents 并行（写章并行不阻塞）

---

## Phase 1：全书规划

字数约束：2000-2500字，硬上限3000字。

### 依赖关系（开书不依赖蒸馏，写章不依赖章纲）

```
Phase 1.0 设定模板 ──→ Phase 1.1 开书（无依赖，读源文合并文件）
                       │  ├── A1：新书设定（书名/类型/卖点/人设/世界观/NPC映射）
                       │  └── A2：全书弧线（情感曲线/角色成长/伏笔/转折点）
                       │
开书完成后 ──→ 初始化真相（记录初始角色状态+时间线）
              └── 注入章节意图（为每个 plot_guide 追加意图字段）

  开书 + plot + de-ai + 注入完成后 ──→ Phase 2 写章（直出，写章agent读取 plot_guide + de-ai_guide + 全书弧线 + 真相）
                   │
              每批写完后 ──→ 批后处理（汇总状态→冲突检测→修复→更新真相）
                   ↓
              下一批写章（读取最新真相，避免跨章矛盾）
                   │
                   └── Phase 0 蒸馏（与开书完全并行，不阻塞）
                       ├── plot（流式到达，注入后再启动写章）
                       ├── de-ai（plot完成后启动，写章阻塞等待）
                       └── style（plot完成后启动，与写章并行不阻塞，可选读）
```

### 1.0 创建设定模板

```bash
python .agents/skills/story-engine/tools/create_templates.py setup <章节数> <设定目录>
```

### 1.1 开书（2 agents 串行，无依赖）

| 顺序 | Agent | Task prompt | 输出 |
|------|-------|-------------|------|
| 1 | A1：新书设定 | arc-concept.md | 设定/新书设定.md + 设定/简介.md |
| 2 | A2：全书弧线 | arc-skeleton-core.md | 设定/全书弧线.md |

⚠️ 开书不依赖蒸馏，可与 Phase 0 并行。

### 1.2 全书章节顺序映射

Task prompt：`prompts/chapter-mapping.md`

---

## 开书编排（agent 自动执行）

### Step 0：定位源文

检查用户提供的路径或扫描 `novel-download-authors/{作者名}/{源书名}.txt`（合并文件）。

### Step 1：创建项目目录 + 设定模板

```bash
python .agents/skills/story-engine/tools/create_templates.py setup <章节数> <设定目录>
```

### Step 2：蒸馏（与开书完全并行）

加载 story-style skill。plot 优先，流式到达。de-ai 在 plot 完成后启动。写章需等 plot + de-ai + 开书 + 注入完成后才启动。

### Step 2.5：生成情节概览（可选，plot 全部完成后执行）

```bash
python .agents/skills/story-engine/tools/extract_plot_overview.py <蒸馏目录> <设定目录>/plot_overview.md
```

### Step 3：开书（2 agents 串行，无依赖）

| 顺序 | Agent | 输出 |
|------|-------|------|
| 1 | A1：新书设定 | 设定/新书设定.md + 设定/简介.md |
| 2 | A2：全书弧线 | 设定/全书弧线.md |

### Step 3.5：初始化真相（开书完成后执行）

Task prompt：`prompts/init-truth.md`
输出：仿写/{新书名}/追踪/真相.md

### Step 3.6：注入章节意图（开书完成后执行）

```bash
python .agents/skills/story-engine/tools/inject_chapter_intent.py <全书弧线.md> <蒸馏目录>
```
为每个 plot_guide_N.md 合并章节意图字段（写章目标+位置+推进目标+伏笔+过期债务）。

### Step 3.7：校验章节映射

```bash
python .agents/skills/story-engine/tools/verify_chapter_mapping.py <章节顺序.md> <蒸馏目录>
```
检查映射是否完整、无重复、源文 plot_guide 是否存在。失败则中断。

### Step 4：写章（流式，10 agents × N批循环）

等待所有 plot_guide 和注入完成后启动。写章agent直接读取 plot_guide（含章节意图）+ de-ai_guide（精确计数）+ 全书弧线 + 新书设定 + 真相，跳过章纲。

⛔ **一次出稿，不准重写**。写章agent写完后直接回传，不跑 verify_chapter.py 校验指纹，不因此重写。如果指纹偏差大，调 tolerance 或改 gen_guide 目标，不在写章时迭代。

每批写完后执行 **Step 4.5 批后处理**，再启动下一批。

### Step 4.5：批后处理（每批写完后执行）

Task prompt：`prompts/post-batch.md`
- 汇总本批各章回传的状态变更
- 检测冲突（角色位置/关系阶段/伏笔状态）
- 自动修复矛盾段落
- 更新追踪/真相.md

### Step 5：导出

```bash
cat 仿写/{新书名}/正文/*.txt > 仿写/{新书名}/{新书名}.txt
```

### Step 6：时间报告

```bash
python .agents/skills/story-engine/tools/timer.py report --session "vplan-{新书名}" --output "仿写/{新书名}/timing_report.md"
```
