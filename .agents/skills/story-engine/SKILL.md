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

## 文件结构

```
projects/{作者名}/{源书名}/
├── _cache/chapters/第N章.txt        # 拆章缓存
└── rewrites/{新书名}/
    ├── concept.md                    # 新书设定 + 全书弧线（含固定角色名）
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

## Pipeline（4 阶段 + 自动导出）

```
Phase 1:   开书 (pro, 1 call)        → concept.md
Phase 1.5: 风格分析 (脚本)            → style_analysis/style_{N}.json + style_{N}.md（模板）
Phase 2:   Guides (flash, 2N 并行)   → plot_{N}.md + style_{N}.md（引用模板）
Phase 3:   写章 (flash, N 并行)      → ch_{N}.txt（章名自生成）
Phase 3.5: Trim (flash)              → 超字数 20% 的章自动精简
Phase 3.6: 衔接修复 (flash, N-1 并行) → 修章间重叠
Phase 4:   对比 (本地)                → compare/报告
Phase 5:   自动导出                    → export/{书名}.txt（写章完成后自动执行）
```

## Agent/API 双模式

通过 `prompt_loader.py` 实现同一套 prompt 两种模式通用：
- **Agent 模式**：Claude 自行 Read 文件
- **API 模式**：自动解析 `【标签】路径` → 嵌入文件内容 → 调 API

## 使用

```bash
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
| `open-book.md` | 开书 | 源文样本（首/前/25%/50%/75%/尾，覆盖全书弧线） | concept.md（设定+弧线+角色名） |
| `plot-guide.md` | 章纲 | 源文第N章 + concept | 节拍映射表 + 换皮检验 |
| `style-guide.md` | 风格 | 源文第N章 | 定量锚点 + 去AI指令 |
| `write-chapter.md` | 写章 | plot_guide + style_guide | ch_{N}.txt |

## 配套 Skills

| Skill | 用途 | 触发词 |
|-------|------|--------|
| `story-blurb` | 书名+简介生成 | 「写简介」「书名」 |
| `story-cover` | 封面生成（默认输出prompt） | 「封面」「生成封面」 |
| `story-compare` | 对比报告 | 「跑对比」「对比」 |
| `story-style` | 源文风格分析 | 「分析风格」「提取风格」 |
| `story-scan` | 番茄排行榜分析 | 「番茄扫描」「番茄数据」 |

## 对比

```bash
python .agents/skills/story-compare/compare.py "<项目目录>" <起始章> <结束章>
```

## 导出

```bash
python tools/merge_chapters.py <项目目录>/chapters/ <项目目录>/export/新书.txt
```
