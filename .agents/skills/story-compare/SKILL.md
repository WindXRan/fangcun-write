---
name: story-compare
description: |
  快速生成仿写书与源文的逐章对比文件，用于投稿前质量评估或问AI哪本更好。
trigger:
  - /story-compare
  - /对比
  - 对比
  - 生成对比
  - 看看对比
---

# story-compare：仿写对比文件生成

通过脚本生成 `{书名}/对比/对比_{start}-{end}.md`，无 AI 参与，纯数据对比 + 全文对照。

## 工具

| 脚本 | 用途 |
|------|------|
| `compare.py` | 逐章对比（字数/全文对照） |
| `concept_compare.py` | **开书设定对比清单** — 写章前审阅设定换皮完整性 |
| `local_compare.py` | 本地对比报告（脚本定量 + LLM定性） |
| `tools/auto_compare.py` | API 抄袭风险分析（调 LLM 评估） |

### CLI 用法

```bash
# 逐章对比（纯本地，无 AI）
python .agents/skills/story-compare/compare.py "{书名}" 1 10 [--source {作者名}/{源书名}]

# 开书设定对比清单（写章前必跑，算法检查）
python .agents/skills/story-compare/concept_compare.py "{书名}" [--source 作者/源书名]

# 本地对比报告（脚本定量 + LLM定性）
python .agents/skills/story-compare/local_compare.py --config configs/xxx.json --start 1 --end 10

# 抄袭风险分析（调 API）
python .agents/skills/story-compare/tools/auto_compare.py --config configs/xxx.json --start 1 --end 10
```

## 用法

```
/story-compare {书名}                  # 默认黄金三章（第1-3章）
/story-compare {书名} 1 10             # 指定区间

# 开书设定对比清单（写章前检查）
/story-compare --concept {书名}
```

## 执行

```bash
python .agents/skills/story-compare/compare.py "{书名}" [起始章] [结束章] [--source {作者名}/{源书名}]
```

**源文查找优先级**：
1. 仿写目录下的`源文章节/`子目录（最可靠）
2. `新书概念.md`中的`源文路径`字段
3. `--source`参数指定的`projects/{作者名}/{源书名}/_cache/chapters/`目录
4. 同作者目录下搜索
5. 全局搜索（兜底，可能匹配到错误的书）

**建议**：始终使用`--source`参数指定源文路径，避免全局搜索匹配错误。

## 输出

生成 `{书名}/对比/对比_{start}-{end}.md`，结构：

1. **统计对比表**（所有章节汇总，一目了然）
2. **版本A（源文）**（全部章节连着放，方便连续阅读）
3. **版本B（新书）**（全部章节连着放，方便连续阅读）

## 字数统计

**使用番茄标准**：所有非空格字符（汉字+标点+数字+英文）

## 开书设定对比清单（concept_compare）

在生成 guides 和写章前运行，比对源文 vs 新书的概念设定，输出结构化 checklist。

### 检查内容

| 模块 | 检查项 | 方式 |
|------|--------|------|
| 元信息 | 书名/作者/分类/标签对比 | 算法 |
| 角色设定 | 角色类型、年龄、设定比对 | 算法 |
| 角色名 | 源文 vs 新书角色名重叠检测 | 算法 |
| AI命名 | 检测诗意字/古风生僻字等 AI 通病 | 算法 |
| 核心冲突 | 冲突类型自动分类，检测是否已换 | 算法 |
| 换皮要点 | concept.md 中的换皮列表完整性 | 算法 |
| 世界观 | 时代背景、场景名重叠检测 | 算法 |
| 风险汇总 | 高/中/低风险分级，给出是否可写章建议 | 综合 |

### 用法

```bash
# 基础检查（自动推导源书路径）
python .agents/skills/story-compare/concept_compare.py "傅总的全能助理"

# 指定源书路径
python .agents/skills/story-compare/concept_compare.py "傅总的全能助理" --source "闻栖/林助理颠颠的，总裁他超爱"
```

### 输出

生成 `rewrites/{书名}/compare/开书设定对比清单.md`，包含：

1. **元信息对比** — 源书 vs 新书基础信息
2. **角色设定对比表** — 角色/年龄/设定/人设模式/换皮判定
3. **角色名重叠检测** — 精确到完全匹配/单字重叠
4. **AI命名通病检测** — 诗意字/古风字标记
5. **核心冲突对比** — 冲突类型自动分类+变更判定
6. **换皮要点清单** — concept.md 中声明的换皮项
7. **世界观对比** — 时代/场景重叠
8. **换皮检验清单** — 6 项 check，一目了然
9. **风险汇总+结论** — 高风险项必须修复后才可推进写章

### Pipeline 位置

```
open-book (开书) → concept_compare.py (设定检, BEFORE guides) → guides → write → ...
```

必检红线（输出中标记 🔴 高）：
- **核心冲突类型未变更** → 必须重设计
- **角色名完全重叠** → 必须改名

## 注意事项

1. 默认只比黄金三章，如需全书加 `1 9999`
2. 源文自动检测：优先从 concept.md 的 `源文路径` 字段读取，未找到则搜索 `projects/` 目录（兼容旧 `projects/`）
3. 只对比有正文的章节
4. 新书目录结构：`rewrites/{新书名}/chapters/ch_NNN.txt`
