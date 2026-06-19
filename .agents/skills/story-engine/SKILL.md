---
name: story-engine
description: |
    仿写引擎 guide模式：开书→生成guide→写章→对比。
    每章2个guide（plot+style），写章agent只管拿着guide写。
    触发条件：用户说「仿写」「用vPlan写」「帮我仿写这本书」「写第N章」「继续写」。
    不要在用户只是问「怎么写小说」「帮我写大纲」时触发。
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(cp *) Bash(mkdir *)
shell: powershell
---

# story-engine（guide模式）

> 开书→生成guide→写章→对比。只仿骨架，不仿血肉。

## 执行模式（必须遵守）

**禁止自行读取源文并生成内容！必须通过脚本调用API。**

正确的执行方式：
```bash
# 设置API密钥
$env:API_KEY = "sk-xxx"

# 运行脚本（新模块化结构）
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase open-book
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase guides --start 1 --end 3
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase write --start 1 --end 3

# 向后兼容（旧入口仍然可用）
python .agents/skills/story-engine/tools/rewrite_chapters.py --config configs/xxx.json --phase open-book
```

错误的执行方式（禁止）：
- 自己读取源文文件
- 自己分析内容并生成plot_guide/style_guide
- 自己调用prompt_loader.py

**原因**：Agent模式生成的质量不稳定，API模式通过脚本有更好的错误处理、重试机制和质量验证。

## 代码结构（模块化重构后）

```
.story-engine/tools/
├── pipeline.py              # 主pipeline编排器（推荐入口）
├── rewrite_chapters.py      # 向后兼容入口（薄包装层）
├── state_manager.py         # 状态管理器（持久化state.json）
├── utils.py                 # 公共工具函数（缓存、进度、重试）
├── prompt_loader.py         # prompt加载器
├── merge_chapters.py        # 章节合并导出
├── extract_book_data.py     # 提取book_data.json
├── unified_fixer.py         # 多 Agent 审改系统（审查+修复）
├── lib/                     # 共享库
│   ├── api_client.py        # API客户端（带重试）
│   ├── constants.py         # 常量定义
│   ├── text_metrics.py      # 文本指标计算器
│   ├── plagiarism.py        # 抄袭检测
│   ├── source_locator.py    # 源文定位器
│   └── progress.py          # 进度显示
└── phases/                  # 各阶段实现
    ├── __init__.py
    ├── open_book.py         # Phase 0-1: Prep + 开书
    ├── guides.py            # Phase 2-2.5: Guide生成 + 衔接修复
    ├── write.py             # Phase 3: 写章
    ├── validate.py          # Phase 3.1: 质量验证
    ├── postprocess.py       # Phase 3.2-3.8: 后处理（精简/重写/润色/扩写）
    ├── compare.py           # Phase 4: 对比
    ├── review.py            # Phase 4.5-5: 审稿修复
    └── unified.py           # Phase 6: 统一审查修复
```

## 文件结构

```
projects/{作者名}/{源书名}/
├── _cache/
│   └── chapters/第N章.txt        # 拆章缓存
└── rewrites/{新书名}/
    ├── concept.md                    # 精简索引（速查角色名+主线）
    ├── state.json                    # 状态文件（自动管理）
    ├── 完本报告.md                   # 完本报告（自动生成）
    └── settings/
        ├── characters.md             # 角色设定
        ├── world.md                  # 世界观设定
        ├── plot.md                   # 剧情设定
        ├── book_info.md              # 书籍信息
        └── source_analysis.md        # 源文分析
    ├── guides/
    │   ├── plot_{N}.md              # 章纲：源文→新书 节拍映射表 + 换皮检验
    │   └── style_{N}.md             # 风格指南：定量锚点 + 去AI指令
    ├── chapters/
    │   └── ch_{N}.txt               # 正文
    ├── compare/                      # 对比报告
    └── export/                       # 导出文件
        └── {书名}.txt
```

## 方法论

**仿写 = 只拿骨架，不拿血肉。**
- 利益冲突必须换，动作与反应全部换
- 情绪强度和顺序一一对应
- 换皮检验：剥掉人名地名，读者认不出抄了谁 → 合格

详见 `网文小说仿写教学.md`

## Pipeline（5 步主流程）

```
导入 → 开书 → 写章 → 审改 → 导出
```

| 步骤 | phase 名 | 内容 | 输出 |
|------|----------|------|------|
| 1. 导入 | `import` | 拆章+生成header/toc | _cache/chapters/ |
| 2. 开书 | `open` | 设定+概念+风格分析 | settings/ + concept.md |
| 3. 写章 | `write` | guides→写章→验证→后处理 | chapters/ch_{N}.txt |
| 4. 审改 | `review` | 对比+统一审改 | compare/ + unified_review_fix.json |
| 5. 导出 | `export` | 合并导出txt | export/{书名}.txt |

**写章后按需执行（选一个）：**

| 条件 | phase | 说明 |
|------|-------|------|
| 字数超 20% | `trim` | 精简 |
| 人设崩塌/节奏失控 | `rewrite` | 整章重写 |
| 文笔需打磨 | `polish` | 润色 |
| 字数不够 | `expand` | 扩写 |

**单步调试：**
- `prep` / `open_book` / `guides` / `write-only` / `validate` / `compare` / `postfix` / `unified`

## 试水+续写工作流

**场景**：先写10万字试水看能不能签约，签约后再续写全书。

### 触发词识别

| 用户说 | AI执行 |
|--------|--------|
| "仿写这本书" | **先问范围**："全书还是先试水？比如先写10万字（约40章）" |
| "先写10万字试试" | 创建 config，设 `initial_chapters`，跑 open+write |
| "继续写" / "往后写" / "续写" | 检查 state.json，从断点续写 |
| "写完剩下的" | 读取已完成章节，--start 设为 last+1 |

### 试水配置

config.json 增加 `initial_chapters` 字段：
```json
{
  "book_name": "新书名",
  "initial_chapters": 38,
  ...
}
```

- `initial_chapters`：首次写章数量（约10万字，按每章2500字估算）
- 开书阶段自动用**全文**分析弧线，不受此字段限制
- 写章阶段自动限制到 initial_chapters 章

### 续写流程

```
1. 检查 state.json → 获取已完成章节列表
2. --start = max(completed) + 1
3. --end = 源文总章数
4. 跳过 open-book（concept 已有）
5. 只跑 guides + write + postfix
```

## 鲁棒性特性

- **API 重试**：429限流/5xx错误/超时 自动指数退避重试（最多3次）
- **章节重试**：失败章节自动重试（最多2轮）
- **超时自适应**：超时后自动翻倍超时时间（600→1200s）
- **配置校验**：启动时校验必填字段和API_KEY
- **源文缓存**：内存+磁盘两级缓存，避免重复IO
- **状态持久化**：state.json 记录每章状态，支持断点续传
- **损坏检测**：跳过已有文件时检查"抱歉"/"无法生成"等AI拒绝特征
- **抄袭检测**：基于8-gram集合匹配，O(n)复杂度
- **进度显示**：实时进度条，显示ETA

## 使用

```bash
# 1. 导入源文
python .agents/skills/story-import/story_import.py "projects/作者/书名/书名.txt"

# 2. 完整流水线（5 步一键）
python tools/pipeline.py --config configs/xxx.json --phase import,open,write,review,export

# 分步执行
python tools/pipeline.py --config configs/xxx.json --phase open          # 开书
python tools/pipeline.py --config configs/xxx.json --phase write         # 写章
python tools/pipeline.py --config configs/xxx.json --phase review        # 审改
python tools/pipeline.py --config configs/xxx.json --phase export        # 导出

# 单步调试
python tools/pipeline.py --config configs/xxx.json --phase guides
python tools/pipeline.py --config configs/xxx.json --phase write-only

# 执行模式（--mode）
python tools/pipeline.py --config configs/xxx.json --phase write --mode api     # 默认，调 API
python tools/pipeline.py --config configs/xxx.json --phase write --mode agent   # opencode 子 agent
python tools/pipeline.py --config configs/xxx.json --phase write --mode debug   # 只输出 prompt，不调 API

# 查看项目状态
python tools/pipeline.py --config configs/xxx.json --status

# 健康检查
python tools/pipeline.py --config configs/xxx.json --health-check
```

## 配置文件

配置文件在 `configs/` 目录下（被 gitignore），需要手动创建。

```json
{
  "book_name": "新书名",
  "author": "源书作者名",
  "source_book": "源书名",
  "api_key": null,
  "model": "deepseek-v4-flash",
  "reasoning_effort": "low",
  "base_dir": ".",
  "prompts_dir": ".agents/skills/story-engine/prompts",
  "rewrites_dir": "projects/{作者名}/{源书名}/rewrites/{新书名}",
  "execution_mode": "api"
}
```

**关键字段说明：**
- `author`：必须与 `projects/` 下的目录名一致（如 "芋圆香芋派"）
- `source_book`：必须与 `projects/{作者}/` 下的目录名一致（如 "临水小厨娘"）
- `rewrites_dir`：仿写输出目录，格式 `projects/{作者}/{源书}/rewrites/{新书}`
- `api_key`：为 null 时从 `$env:API_KEY` 读取，不要写入配置文件

**目录结构要求：**
```
projects/
└── {作者名}/
    └── {源书名}/
        ├── _cache/
        │   └── chapters/第N章.txt   ← 源文章节
        └── rewrites/
            └── {新书名}/            ← 仿写输出
```

## Prompts

| Prompt | 用途 | 输入 | 输出 |
|--------|------|------|------|
| `open-book.md` | 开书 | 源文样本（首/前/25%/50%/75%/尾，覆盖全书弧线） | settings/ + concept.md（设定+弧线+角色名） |
| `blurb.md` | 书名+简介 | book_info.md + characters.md + 源文头部 | 5书名 + 5简介，番茄爆款对标 |
| `plot-guide.md` | 章纲 | 源文第N章 + concept + 样板库 | 节拍映射表 + 换皮检验 |
| `write-chapter.md` | 写章 | plot_guide + concept + 源文全文 | ch_{N}.txt |
| `trim-chapter.md` | 精简 | 超字数章节 | 精简后章节 |

## 知识库（样板库）

plot-guide 生成时按需参考的写作技巧库。

```
knowledge/
├── INDEX.md                 # 总索引：文件路径→内容描述速查
├── plot/                    # 情节结构技巧
│   ├── character-entry.md   # 人物入场方式（T1-T4）
│   ├── scene-cut.md         # 场景切入方式（S1-S3）
│   ├── chapter-link.md      # 章间衔接方式（C1-C5）
│   ├── hook.md              # 开篇钩子技巧（K1-K4）
│   ├── side-character.md    # 配角功能技巧（P1-P2）
│   ├── relationship.md      # 关系突破技巧（R1-R3）
│   ├── meet-cute.md         # 相遇方式技巧（M1-M4）
│   └── original-plot.md     # 原创情节框架（F1-F4）
└── style/                   # 文笔技巧
    ├── description.md       # 描写技巧（D1-D4）
    ├── dialogue.md          # 对话技巧
    ├── sentence.md          # 句式技巧
    ├── pronoun-density.md   # 代词密度控制
    ├── metaphor.md          # 比喻技巧
    └── object-arrangement.md # 物象排列模板
```

### 加载规则
- 写 plot_guide，如需结构参考 → 加载 knowledge/INDEX.md（总索引 + key rules）
- 写 style_guide，如需文笔参考 → 加载 knowledge/INDEX.md（总索引 + key rules）
- 如需特定技巧详情 → 加载对应的 plot/X.md 或 style/Y.md

## 配套 Skills

| Skill | 用途 | 触发词 | engine 委托 |
|-------|------|--------|------------|
| `story-import` | 标准化导入（拆章+生成header/toc） | 「导入」「import」 | Phase 0 |
| `story-export` | 标准化导出（合并章节为完整txt） | 「导出」「export」 | Phase export |
| `story-trend` | 热梗调研+知识库构建 | 「热梗调研」「搜热梗」「热点调研」 | Phase 1（可选） |
| `story-review` | 审稿（分批+汇总）、修复、审改闭环 | 「审稿」「review」 | Phase 4.5/5 |
| `story-compare` | 对比报告、抄袭风险分析 | 「跑对比」「对比」 | Phase 4 |
| `story-optimize` | 自动评分、规则沉淀 | 「优化prompt」 | — |
| `story-cover` | 封面生成（默认输出prompt） | 「封面」「生成封面」 | — |
| `story-scan` | 番茄排行榜分析 | 「番茄扫描」「番茄数据」 | — |

## 导入

```bash
python .agents/skills/story-import/story_import.py "projects/作者/书名/书名.txt"
```

## 导出

```bash
python .agents/skills/story-export/story_export.py "projects/作者/书名/rewrites/新书名"
```

```bash
python tools/merge_chapters.py <项目目录>/chapters/ <项目目录>/export/新书.txt
```
