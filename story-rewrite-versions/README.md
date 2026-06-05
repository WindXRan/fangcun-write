# story-rewrite 三版本对照

本地完整保存了三个版本的 story-rewrite skill，方便对比演进。

## 版本对应

| 版本 | commit | 日期 | 用途 |
|------|--------|------|------|
| **v1** | `547683c` "仿写引擎核心原则：骨架保留，血肉必须换" | 2026-06-04 之前 | 早期版本：单agent串行、真相文件、审稿体系 |
| **v2** | `7168cf9` "升级story-rewrite到2.0版" | 2026-06-04 | 2.0版：合规标准、风险自测表、验证脚本 |
| **v3** | `test-rewrite/`（当前） | 2026-06-05 之后 | 合并版：v1质量工具 + v2防抄袭 + Mode B 三轮并行Agent |

## 目录结构

```
story-rewrite-versions/
├── v1/                  # 早期版本
│   ├── SKILL.md
│   ├── prompts/         # auditor/de-ai/style-analysis 等
│   ├── tools/           # post-process/scan-quality/word_count 等
│   ├── auditor.md
│   ├── reviser.md
│   └── truth-files.md
│
├── v2/                  # 2.0版（精简+验证脚本）
│   ├── SKILL.md         # 148行（v1的SKILL.md有283行）
│   ├── prompts/
│   ├── tools/           # 新增 validate_files.py
│   └── truth-files.md
│
└── v3/                  # 当前在用的 test-rewrite
    └── test-rewrite/    # 完整 skill 目录
        ├── SKILL.md     # 584行
        ├── prompts/     # 8维风格分析 + 11条去AI规则
        ├── scripts/     # style_analyzer / source_chapter_splitter / validate_files
        ├── tools/       # post-process/word_count
        └── truth-files.md
```

## 三版核心差异

### v1 → v2 演进（547683c → 7168cf9）

| 维度 | v1 | v2 |
|------|----|----|
| SKILL.md 行数 | 283 | 148（精简） |
| 架构 | 单串行pipeline | 仍是串行但增加验证步骤 |
| 核心思想 | "骨架保留，血肉必须换" | "合规仿写 = 跨书融合 + 100%原创内容" |
| 新增内容 | — | 风险自测表、平台查重标准、validate_files.py、validate-aigc.ps1 |
| 删除内容 | — | 旧的长篇拆文相关冗余prompt |

### v2 → v3 演进（7168cf9 → test-rewrite）

| 维度 | v2 | v3 |
|------|----|----|
| 架构 | 单agent串行 | Mode B 三轮并行子agent（B1风格分析 / B2章纲 / B3写章） |
| 风格分析 | 单次LLM分析 | 双层蒸馏：style_analyzer.py（统计指纹）+ LLM 8维分析 |
| 真相文件 | 必填（5个） | 可选（章纲即真相） |
| 章纲 | 锁定事件类型（洗稿风险） | 不锁事件类型，只学节奏 |
| 防抄袭 | 事后审计 | 事前控制（Lv1打乱顺序 / Lv2替换触发逻辑 / Lv3原创支线） |
| 字数硬约束 | 软建议 | 2000-2500字硬上限3000字 |

## 当前用哪个

**v3（test-rewrite）**。v1/v2 本地保存作历史参考，**不删除**。

## 取舍

v3 解决了 v2 的"质量工具链 vs 防止抄袭"二选一难题：
- 借鉴 v1 的：33维审计、de-ai系统、双层蒸馏、真相文件（可选）
- 借鉴 v2 的：合规标准、风险自测表、章纲不锁事件类型、验证脚本
- 新增：Mode B 三轮并行Agent架构、风格指纹统计脚本、3级去重体系

v3 仍有未解决问题：句长偏移（new book 14字 vs source 22字，差-8字），目前无强约束。
