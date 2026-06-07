---
name: story-engine
description: |
    仿写引擎 vPlan：开书→写章。写章agent自己读源文→出guide→写章，不预先蒸馏。
    触发条件：用户说「仿写」「用vPlan写」「帮我仿写这本书」「写第N章」「继续写」。
    全书规划（弧线+映射）在写作前完成，写章阶段直出+批后冲突检测。
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
├── {源书名}.txt                 # 原文合并文件

仿写/{新书名}/
├── 设定/
│   ├── 新书设定.md（书名+类型+卖点+人设+NPC映射+世界观）
│   ├── 全书弧线.md（情感曲线+角色成长+伏笔+转折点）
│   ├── 简介.md（3种风格）
│   ├── 章节顺序.md
│   └── guides/                  # 写章副作用产物
│       ├── plot_guide_N.md     # 写章时生成
│       └── de-ai_guide_N.md    # 脚本生成
├── 追踪/
│   └── 真相.md（时间线+角色状态+伏笔状态）
└── 正文/第N章.txt
```

## Pipeline

```
开书（弧线+设定） ──→ 写章（10 agents × N批）
                            │
                      读源文第N章
                      读弧线+真相+设定
                      出 plot_guide（副产品，保存供批后处理）
                      跑 gen_script 出 de-ai_guide
                      写正文第N章（一次出，不校验不重写）
                            │
                      每批写完 → 批后处理（汇总+冲突检测+更新真相）
                            ↓
                      下一批写章
```

---

## 开书编排

### Step 0：定位源文

检查用户提供的路径或扫描 `novel-download-authors/{作者名}/{源书名}.txt`（合并文件）。

### Step 1：创建项目目录 + 设定模板

```bash
python .agents/skills/story-engine/tools/create_templates.py setup <章节数> <设定目录>
```

### Step 2：开书（2 agents 串行）

| 顺序 | Agent | Task prompt | 输出 |
|------|-------|-------------|------|
| 1 | A1：新书设定 | arc-concept.md | 设定/新书设定.md + 设定/简介.md |
| 2 | A2：全书弧线 | arc-skeleton-core.md | 设定/全书弧线.md |

### Step 3：初始化真相

Task prompt：`prompts/init-truth.md`
输出：仿写/{新书名}/追踪/真相.md

### Step 4：章节映射

Task prompt：`prompts/chapter-mapping.md`
输出：设定/章节顺序.md

### Step 5：写章（10 agents × N批）

每批10章并行，每个写章 agent 的工作流：

1. 读源文：`novel-download-authors/{作者名}/{源书名}/源文/第N章.txt`
2. 读弧线+设定+真相
3. 运行 plot-guide-task.md 生成 `plot_guide_N.md`（保存到 `设定/guides/`）
4. 运行 `tools/verify_chapter.py --gen-guide <源文> -o 设定/guides/de-ai_guide_N.md`
5. 运行 write-chapter.md 写 `正文/第N章.txt`
6. 回传：本章状态变更（角色状态/关系/伏笔等）

⛔ **一次出稿**。不回传指纹，不跑校验，不重写。

### Step 5.5：批后处理

Task prompt：`prompts/post-batch.md`
- 汇总本批各章回传的状态变更
- 检测冲突（角色位置/关系阶段/伏笔状态）
- 更新追踪/真相.md

### Step 6：下一批

重复 Step 5 → Step 5.5 直到所有章节写完。

### Step 7：导出

```bash
cat 仿写/{新书名}/正文/*.txt > 仿写/{新书名}/{新书名}.txt
```
