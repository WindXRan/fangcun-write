---
name: story-style
description: |
  写作风格管理引擎。风格注册、发现、验证，供 story-rewrite 以 --style 参数调用。
  触发方式：/story-style、/文风、「有什么风格」「风格列表」「用XX风格写」
  自动化：女娲（huashu-nuwa）蒸馏网文作者时自动注册新风格。
---

# story-style：写作风格管理引擎

> 风格的家。每个风格是一个独立目录，含 SKILL.md + meta.json + references/。

## 核心职责

`story-style` 是风格系统的**唯一知识源**，承担三项职责：

| 职责 | 说明 |
|------|------|
| **注册与发现** | 管理文风库，扫描 `skills/story-style/*/SKILL.md` 自动发现可用风格 |
| **风格知识源** | 每个风格的 SKILL.md 包含完整的写作指导，agent 通过 read 工具直接读取 |
| **兼容性验证** | 验证 SKILL.md 结构完整、体裁兼容性 |

## 目录结构

```
skills/story-style/
├── SKILL.md                    # 本文件（管理引擎）
├── templates/
│   └── meta.json               # 风格创建模板
└── {name}/                     # 每个风格一个目录
    ├── SKILL.md                # 女娲蒸馏出的文风 Skill（独立可用）
    ├── meta.json               # 风格元数据
    └── references/             # 调研资料
        ├── research/           # 调研产物（01-06.md + corpus_stats/）
        └── sources/            # 一手素材（原文txt等）
```

## 文风列表

| 文风 | 目录 | 描述 | 体裁 | status |
|------|------|------|------|--------|
| 闻栖(v2) | `wenqi/` | 女频·模版化开篇·短章铁律·量化DNA·信息钩结尾 | 现代言情/古代言情/穿书/重生 | ✅ 可用 |

---

## 风格发现

**自动扫描规则**：目录下存在 `SKILL.md` + `meta.json` → 注册为可用风格。

`meta.json` 必须包含 `name`、`source_skill` 两个字段。缺任一则该风格不可用。

---

## 风格加载

`story-rewrite` 发起 `--style={name}` 请求时：

1. 读取 `skills/story-style/{name}/meta.json` 获取元数据
2. 按 `meta.source_skill` 读取 `skills/story-style/{name}/SKILL.md`
3. agent 通过 read 工具直接从 SKILL.md 获取：表达DNA、写作心智模型、决策启发式、章纲模板、质量检查清单

**不需要 injection 提取**。agent 直接读 SKILL.md 原文，自己定位需要的 section。

---

## 验证

### 风格健康检查

可手动执行：验证一个风格的 SKILL.md 是否满足最低标准。

检查清单：
- [ ] `source_skill` 文件存在
- [ ] SKILL.md 包含 `## 表达DNA` section（≥5个量化特征）
- [ ] SKILL.md 包含 `## 核心写作心智模型` section（≥3个）
- [ ] SKILL.md 包含 `## 可运行的写作模板` section（章纲骨架）
- [ ] SKILL.md 包含 `## 质量检查清单` section
- [ ] `chapter_word_count` 范围合理（min < target < max）

### 风格质量基线

每个风格必须满足以下最低标准，否则不可用于 story-rewrite：

| 维度 | 最低标准 | 验证方式 |
|------|---------|---------|
| **表达DNA** | ≥5个量化特征（句式、转折词、动词、口癖、章节模式） | SKILL.md 包含该 section |
| **写作心智模型** | ≥3个（如开篇结构、糖点密度、结尾钩子） | SKILL.md 包含该 section |
| **章纲模板** | 必须有（感情线/剧情线骨架） | SKILL.md 包含该 section |
| **质量检查清单** | 必须有（黄金三章自查、写作过程自查等） | SKILL.md 包含该 section |
| **字数统计** | 有全量统计或手动标注 | `chapter_word_count` 合理 |

**质量评级**：

| 评级 | 标准 | 可用场景 |
|------|------|---------|
| ⭐⭐⭐ | 满足所有基线 + 有全量统计 + 有章纲模板 | story-rewrite 全功能 |
| ⭐⭐ | 满足基线 + 有章纲模板 | story-rewrite 基本功能 |
| ⭐ | 满足基线 | story-rewrite 降级模式（无章纲模板） |
| ❌ | 不满足基线 | 不可用于 story-rewrite |

### 自动验证机制

nuwa 蒸馏完成后，自动执行以下验证流程：

1. 验证 meta.json 格式
2. 验证 SKILL.md 包含必要 section
3. 检查质量基线

**验证通过** → 自动注册到文风列表，输出质量评级
**验证失败** → 报告缺失项，不注册

### nuwa + style 联动流程

```
用户：蒸馏XX作者
    ↓
nuwa Phase 0.5：创建目录 + 全量统计
    ↓
nuwa Phase 1-3：调研 + 提炼 + 构建 SKILL.md
    ↓
nuwa Phase 4：自动创建 meta.json + 验证
    ↓
story-style：自动注册到文风列表
    ↓
story-rewrite：--style={name} 可用
```

---

## 从女娲创建新风格

### 自动模式

用 `女娲（huashu-nuwa）` 蒸馏网文作者时，检测到「网文作者/番茄/女频/男频」等关键词，自动：
1. 创建 `skills/story-style/{name}/SKILL.md`
2. 创建 `skills/story-style/{name}/meta.json`（参考 `templates/meta.json`）
3. 更新本文风列表

### 手动模式

1. 创建 `skills/story-style/{name}/SKILL.md`（女娲蒸馏产物）
2. 创建 `skills/story-style/{name}/meta.json`（参考 `templates/meta.json`）
3. 验证 SKILL.md 结构完整（执行上方检查清单）
4. 更新本文风列表

### meta.json 创建规范

参照 `templates/meta.json` 的结构，从蒸馏结果自动填充：

| meta.json 字段 | 填充来源 |
|---------------|---------|
| `name` | 风格英文名（frontmatter的name去掉-perspective后缀） |
| `label` | 中文名+简短标签 |
| `description` | frontmatter的description前50字 |
| `source_skill` | `skills/story-style/{name}/SKILL.md` |
| `compatible_genres` | frontmatter的trigger中提取的题材词 |
| `chapter_word_count` | 全量统计中的均值±标准差，无则用默认2,200 |
| `features.dialogue_ratio` | 来自全量统计的 cross-book-stats.json |

---

## 使用方式

```
# 路由到 story-rewrite，加载闻栖风格写全书
/story-rewrite --style=wenqi

# 路由到 story-rewrite-preview，试水3章
/story-rewrite-preview --style=wenqi

# 查看可用风格
/story-style

# 验证某个风格是否可用
/story-style --validate=wenqi
```

## story-rewrite 加载路径

story-rewrite 通过以下路径加载风格：
1. 读取 `skills/story-style/{name}/meta.json` 获取元数据
2. 按 `meta.source_skill` 读取 `skills/story-style/{name}/SKILL.md`
3. agent 通过 read 工具直接从 SKILL.md 获取完整风格信息（表达DNA、写作心智模型、决策启发式、章纲模板等）
