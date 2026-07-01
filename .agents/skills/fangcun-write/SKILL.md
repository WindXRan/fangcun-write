---
name: fangcun-write
version: 6.1.0
description: |
  方寸长篇仿写引擎。三阶段：脑洞→评估→写作。前后互锁，不过不写。
---

# 方寸使用说明

## 你说什么，我做什么

| 你说 | 我做 |
|------|------|
| **「开书 仿写/原创」** | 三阶段自动跑：脑洞→评估→写章准备 |
| **「写第N章」** | preflight→章纲→写章→审查→修复→门禁 |
| **「检查/审计」** | quality_checker全量扫描，exit code堵死 |
| **「修复」** | 自动修P0/P1问题（角色名泄露/角色卡缺失/称谓换皮） |

## 三阶段工作流

```
阶段一：脑洞                   阶段二：评估                   阶段三：写作
─────────                     ─────────                    ─────────
开书脑洞 → 出3-5套方案          开书评估 → 双线打分            fanxie-chapter
每套带市场评估                  市场≥16/20 换皮≥32/40          + quality_gate
                                ↓                           + quality_checker
                               ← 不及格打回脑洞 ←            出口碑章节
```

## 工具清单

| 阶段 | 工具 | 一句话 |
|:----:|------|--------|
| 🧠 | `开书脑洞` | 给源文/方向，出N套带市场评估的换皮方案 |
| 📊 | `开书评估` | 双线评估（市场+换皮），不及格打回 |
| 📋 | `world-mapper` | 评估通过后，按方案生成完整映射表+角色卡 |
| ✍️ | `fanxie-chapter` | 按章纲写正文 |
| ✍️ | `guide-convert` | 源文章纲→仿写章纲翻译 |
| 🔒 | `quality_checker.py` | 代码级验证，exit code=0才通过 |
| 🔒 | `quality-gate` | prompt级质量门禁，preflight/chapter/audit三模式 |
| 🔧 | `fanxie-structural-fix` | 逐beat对齐章纲，修结构偏差 |
| 🔧 | `fanxie-fix` | 修技法偏差（调性/开场/节奏/AI腔） |
| 🔧 | `fanxie-review` | 读者视角审查 |
| 🔧 | `character-split` | 拆复合角色 |
| 🔧 | `deslop` | 去AI味 |

## 可执行管线（pipeline）

定义在 `tools/pipelines/*.xml`，用 `pipeline_runner.py` 执行：

| 管线 | 执行内容 | 一次跑完？ |
|------|---------|:----------:|
| `开书` | 脑洞→评估→world-mapper→验证 | ✅ 开书阶段 |
| `逆推` | 角色→设定→关系→风格→卷纲 | ✅ 全量逆推（章纲除外） |
| `写章` | guide-convert→写章→审查→修复→门禁 | ✅ 章纲存在时 |

调用方式：
```bash
python pipeline_runner.py 开书 input='{"mode":"仿写","source":"全家偷听心声"}' project_dir="projects/沈落葵的江湖"
python pipeline_runner.py 逆推 input='{"source_project":"全家偷听心声"}'
```

## 项目结构

```
projects/XXX/
├── 正文/卷纲/     ← 卷纲
├── 正文/章纲/     ← 章纲
├── 正文/正文/     ← 正文
└── 作品信息/
    ├── 主题/总纲/简介/标签
    └── 设定/角色/关系图谱/原配映射表
```
