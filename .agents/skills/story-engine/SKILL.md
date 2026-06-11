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
├── unified_reviewer.py      # 统一审改系统（审查）
├── unified_fixer.py         # 统一审改系统（修复）
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

## Pipeline（编排器，委托各 phase 执行）

```
Phase 0:   导入 (story-import)        → _cache/chapters/ + _header.txt + _toc.txt
Phase 1:   开书 (pro, 1 call)        → settings/ + concept.md       [open_book.py]
Phase 1.1: Concept审查 (flash)        → 检查人设/冲突/情节是否换皮     [open_book.py]
Phase 1.5: 风格分析 (脚本)            → style_analysis/style_{N}.json [open_book.py]
Phase 2:   Guides (flash, 2N 并行)   → plot_{N}.md + style_{N}.md    [guides.py]
Phase 2.5: Guide衔接修复 (flash)     → 修复章间断裂                    [guides.py]
Phase 3:   写章 (flash, N 并行)      → ch_{N}.txt                    [write.py]
Phase 3.1: 质量验证                    → 字数/比喻/AI路标词/台词抄袭检测 [validate.py]
Phase 3.2: 后处理                      → 去#号/修标题/补省略号          [postprocess.py]
Phase 3.5: Trim (flash)              → 超字数 20% 的章自动精简        [postprocess.py]
Phase 3.6: 整章重写 (flash)           → 人设崩塌/节奏失控时重写        [postprocess.py]
Phase 3.7: 润色 (flash)              → 只改文笔，不改内容             [postprocess.py]
Phase 3.8: 扩写 (flash)              → 增加内容扩充字数               [postprocess.py]
Phase 4:   对比 (本地)                → compare/报告                  [compare.py]
Phase 4.5: 审稿 (分批→汇总)          → 审稿报告 + 汇总报告            [review.py]
Phase 5:   修复 (根据审稿)            → 修复后章节                     [review.py]
Phase 6:   统一审查+修复              → unified_review_fix.json       [unified.py]
Phase 7:   自动导出                    → export/{书名}.txt             [merge_chapters.py]
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
# Phase 0: 导入源文
python tools/story_import.py "projects/作者/书名/书名.txt"

# 完整流水线（推荐）
python tools/pipeline.py --config configs/xxx.json --start 1 --end 10 --workers 10

# 一键完成（生成+审查+修复+报告）
python tools/pipeline.py --config configs/xxx.json --phase all-with-fix --start 1 --end 10

# 分步执行
python tools/pipeline.py --config configs/xxx.json --phase open-book
python tools/pipeline.py --config configs/xxx.json --phase guides
python tools/pipeline.py --config configs/xxx.json --phase write,compare

# 统一审查+修复（推荐）
python tools/pipeline.py --config configs/xxx.json --phase unified --start 1 --end 10

# 查看项目状态
python tools/pipeline.py --config configs/xxx.json --status

# 健康检查（诊断项目问题）
python tools/pipeline.py --config configs/xxx.json --health-check
python tools/pipeline.py --config configs/xxx.json --health-output report.json

# 向后兼容（旧入口）
python tools/rewrite_chapters.py --config configs/xxx.json --phase open-book
```

## 配置文件

```json
{
  "book_name": "仿写书名",
  "author": "作者",
  "source_book": "源书名",
  "trend_dir": "trends/题材名",
  "api_key": null,
  "model": "deepseek-v4-flash",
  "reasoning_effort": "low",
  "prompts_dir": ".agents/skills/story-engine/prompts",
  "rewrites_dir": "projects/作者/源书/rewrites/仿写书",
  "config_file": "configs/xxx.json"
}
```

> ⚠️ `api_key` 为 null 时从 `$env:API_KEY` 读取。不要把 key 写入配置文件。
> 
> 📌 `trend_dir` 可选，指定后开书阶段会自动注入热梗知识库素材。配合 `story-trend` skill 使用。
> 
> 📌 `config_file` 用于审稿修复阶段，指向配置文件路径。

## Prompts

| Prompt | 用途 | 输入 | 输出 |
|--------|------|------|------|
| `open-book.md` | 开书 | 源文样本（首/前/25%/50%/75%/尾，覆盖全书弧线） | settings/ + concept.md（设定+弧线+角色名） |
| `plot-guide.md` | 章纲 | 源文第N章 + concept + 样板库 | 节拍映射表 + 换皮检验 |
| `style-guide.md` | 风格 | 源文第N章 + 样板库 | 定量锚点 + 去AI指令 |
| `write-chapter.md` | 写章 | plot_guide + style_guide | ch_{N}.txt |
| `trim-chapter.md` | 精简 | 超字数章节 | 精简后章节 |

## 知识库（样板库）

plot-guide / style-guide 生成时按需参考的写作技巧库。

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
| `story-trend` | 热梗调研+知识库构建 | 「热梗调研」「搜热梗」「热点调研」 | Phase 1（可选） |
| `story-review` | 审稿（分批+汇总）、修复、审改闭环 | 「审稿」「review」 | Phase 4.5/5 |
| `story-compare` | 对比报告、抄袭风险分析 | 「跑对比」「对比」 | Phase 4 |
| `story-optimize` | 自动评分、规则沉淀 | 「优化prompt」 | — |
| `story-blurb` | 书名+简介生成 | 「写简介」「书名」 | — |
| `story-cover` | 封面生成（默认输出prompt） | 「封面」「生成封面」 | — |
| `story-scan` | 番茄排行榜分析 | 「番茄扫描」「番茄数据」 | — |

## 对比

```bash
python .agents/skills/story-compare/compare.py "<项目目录>" <起始章> <结束章>
```

## 导出

```bash
python tools/merge_chapters.py <项目目录>/chapters/ <项目目录>/export/新书.txt
```
