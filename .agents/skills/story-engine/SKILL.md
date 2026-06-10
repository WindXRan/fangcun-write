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

# 运行脚本
python .agents/skills/story-engine/tools/rewrite_chapters.py --config configs/xxx.json --phase open-book
python .agents/skills/story-engine/tools/rewrite_chapters.py --config configs/xxx.json --phase guides --start 1 --end 3
python .agents/skills/story-engine/tools/rewrite_chapters.py --config configs/xxx.json --phase write --start 1 --end 3
```

错误的执行方式（禁止）：
- 自己读取源文文件
- 自己分析内容并生成plot_guide/style_guide
- 自己调用prompt_loader.py

**原因**：Agent模式生成的质量不稳定，API模式通过脚本有更好的错误处理、重试机制和质量验证。

## 文件结构

```
projects/{作者名}/{源书名}/
├── _cache/chapters/第N章.txt        # 拆章缓存
└── rewrites/{新书名}/
    ├── concept.md                    # 精简索引（速查角色名+主线）
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
    └── compare/                      # 对比报告
```

## 方法论

**仿写 = 只拿骨架，不拿血肉。**
- 利益冲突必须换，动作与反应全部换
- 情绪强度和顺序一一对应
- 换皮检验：剥掉人名地名，读者认不出抄了谁 → 合格

详见 `网文小说仿写教学.md`

## Pipeline（编排器，委托各 skill 执行）

```
Phase 0:   导入 (story-import)        → _cache/chapters/ + _header.txt + _toc.txt
Phase 1:   开书 (pro, 1 call)        → settings/ + concept.md       [engine]
Phase 1.1: Concept审查 (flash)        → 检查人设/冲突/情节是否换皮     [engine]
Phase 1.5: 风格分析 (脚本)            → style_analysis/style_{N}.json [engine]
Phase 2:   Guides (flash, 2N 并行)   → plot_{N}.md + style_{N}.md    [engine]
Phase 3:   写章 (flash, N 并行)      → ch_{N}.txt                    [engine]
Phase 3.1: 质量验证                    → 字数/比喻/AI路标词/台词抄袭检测 [engine]
Phase 3.2: 后处理                      → 去#号/修标题/补省略号          [engine]
Phase 3.5: Trim (flash)              → 超字数 20% 的章自动精简        [engine]
Phase 3.6: 衔接修复 (flash, N-1 并行) → 修章间重叠                    [engine]
Phase 4:   对比 (本地)                → compare/报告                  [story-compare]
Phase 4.5: 审稿 (分批→汇总)          → 审稿报告 + 汇总报告            [story-review]
Phase 5:   修复 (根据审稿)            → 修复后章节                     [story-review]
Phase 6:   自动导出                    → export/{书名}.txt             [story-export]
```

**Phase 1.1 Concept审查**：
- 检查人设模式是否与源文相同（纨绔vs病弱等）
- 检查冲突类型组合是否与源文相同
- 检查情感内核是否与源文相同
- 检查配角名、地名是否与源文重复
- 不通过则要求重新开书

**engine 只做编排，具体逻辑归各 skill：**
- `story-export`：导出为番茄格式txt
- `story-review`：审稿（分批+汇总）、修复、审改闭环
- `story-compare`：对比报告、抄袭风险分析
- `story-optimize`：自动评分、规则沉淀

## 鲁棒性特性

- **API 重试**：429限流/5xx错误/超时 自动指数退避重试（最多3次）
- **超时自适应**：超时后自动翻倍超时时间（600→1200s）
- **配置校验**：启动时校验必填字段和API_KEY
- **源文缓存**：读取过的源文自动缓存，避免重复IO
- **损坏检测**：跳过已有文件时检查"抱歉"/"无法生成"等AI拒绝特征
- **抄袭检测**：基于8-gram集合匹配，O(n)复杂度

## Agent/API 双模式

通过 `prompt_loader.py` 实现同一套 prompt 两种模式通用：
- **Agent 模式**：Claude 自行 Read 文件
- **API 模式**：自动解析 `【标签】路径` → 嵌入文件内容 → 调 API

## 使用

```bash
# Phase 0: 导入源文
python tools/story_import.py "projects/作者/书名/书名.txt"

# 完整流水线
python tools/rewrite_chapters.py --config configs/config_rewrite_10ch.json --start 1 --end 10 --workers 10

# 分步执行
python tools/rewrite_chapters.py --config configs/xxx.json --phase open-book
python tools/rewrite_chapters.py --config configs/xxx.json --phase guides
python tools/rewrite_chapters.py --config configs/xxx.json --phase write,compare
```

## 配置文件

```json
{
  "book_name": "仿写书名",
  "author": "作者",
  "source_book": "源书名",
  "api_key": null,
  "model": "deepseek-v4-flash",
  "reasoning_effort": "low",
  "prompts_dir": ".agents/skills/story-engine/prompts",
  "rewrites_dir": "projects/作者/源书/rewrites/仿写书"
}
```

> ⚠️ `api_key` 为 null 时从 `$env:API_KEY` 读取。不要把 key 写入配置文件。

## Prompts

| Prompt | 用途 | 输入 | 输出 |
|--------|------|------|------|
| `open-book.md` | 开书 | 源文样本（首/前/25%/50%/75%/尾，覆盖全书弧线） | settings/ + concept.md（设定+弧线+角色名） |
| `plot-guide.md` | 章纲 | 源文第N章 + concept | 节拍映射表 + 换皮检验 |
| `style-guide.md` | 风格 | 源文第N章 | 定量锚点 + 去AI指令 |
| `write-chapter.md` | 写章 | plot_guide + style_guide | ch_{N}.txt |

## 配套 Skills

| Skill | 用途 | 触发词 | engine 委托 |
|-------|------|--------|------------|
| `story-import` | 标准化导入（拆章+生成header/toc） | 「导入」「import」 | Phase 0 |
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
