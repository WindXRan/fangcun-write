---
name: story-style
description: |
  写作风格管理引擎。风格注册、发现、验证、injection提取，供 story-rewrite 以 --style 参数调用。
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
| **injection 引擎** | 按 meta.json 定义，从 source_skill 提取 section 注入到 story-rewrite prompt |
| **兼容性验证** | 验证 heading 匹配、injection 非空、体裁兼容性 |

## 目录结构

```
skills/story-style/
├── SKILL.md                    # 本文件（管理引擎）
├── templates/
│   └── meta.json               # 风格创建模板
└── {name}/                     # 每个风格一个目录
    ├── SKILL.md                # 女娲蒸馏出的文风 Skill（独立可用）
    ├── meta.json               # injection 配置 + 元数据
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

`meta.json` 必须包含 `name`、`source_skill`、`injections` 三个字段。缺任一则该风格不可用。

---

## Injection 引擎

### 工作原理

`story-rewrite` 发起 `--style={name}` 请求时，本引擎执行：

```
1. 读取 skills/story-style/{name}/meta.json
2. 校验兼容性（compatible_genres / incompatible_genres）
3. 读取 meta.source_skill 指向的 SKILL.md
4. 遍历 meta.injections，按规则提取 section → 注入到 story-rewrite prompt
5. 注入 meta.chapter_word_count 覆盖字数参数
```

### 提取规则

每个 `injections.{key}` 定义了一组从 SKILL.md 到 prompt 的映射：

| 字段 | 含义 |
|------|------|
| `source_heading` | 从 SKILL.md 的哪个 `##` heading 提取 |
| `source_headings` | 多个 heading 合并提取（数组） |
| `source_sub_headings` | 非空时只提取匹配的子节（`###` heading），跳过不匹配的 |
| `target` | 注入到 story-rewrite prompt 的哪个位置 |

### 注入行为

| target 前缀 | 行为 |
|-------------|------|
| `替换` 开头 | 替换 prompt 中同名 section |
| `追加` 或 `写作原则` 开头 | 追加到同名 section 之后 |
| 带 `预览`/`审查`/`检查` | 对应审查阶段使用 |
| 带 `可选` | 仅在 agent 判断有用时注入 |

### 当前 injection key

| key | source | target | 提取规则 |
|-----|--------|--------|---------|
| `voice` | `## 表达DNA` | `你的声音` | 有 sub_headings 时只取匹配子节，跳过禁用词 |
| `rules` | `## 写作心智模型` + `## 决策启发式` + `## 价值观与反模式` | `写作原则（追加）` | 模型取标题+摘要+证据；启发式全取；反模式取标题行 |
| `quality` | `## 质量检查清单` | `质量检查` | 可选，无则跳过 |
| `templates` | `## 可运行的写作模板` | `模板参考（可选读取）` | 可选，无则跳过 |
| `recovery` | `## 写作恢复手册` | `写作恢复指引（可选读取）` | 可选，无则跳过 |

---

## 验证

### injection 兼容性检查

执行 injection 前自动校验：

| 检查项 | 不通过时 |
|--------|---------|
| `source_heading` 在 SKILL.md 中不存在 | ⚠️ 报告缺失 heading，该 injection 跳过（不静默吞掉） |
| 提取结果为空 | ⚠️ 报告"section 为空"，该 injection 跳过 |
| `incompatible_genres` 命中 | ❌ 报错中止，告知用户该风格不支持当前题材 |
| `meta.json` 缺少必要字段 | ❌ 报错中止，告知哪个字段缺失 |

### 风格健康检查

可手动执行：验证一个风格的 meta.json 与 source_skill 的所有 injection 是否能正常工作。

检查清单：
- [ ] `source_skill` 文件存在
- [ ] 每个 injection 的 `source_heading` 在 SKILL.md 中有对应 `##` heading
- [ ] `voice` injection 提取结果非空
- [ ] `rules` injection 提取结果非空
- [ ] `incompatible_genres` 合理（不会覆盖所有常见题材）
- [ ] `chapter_word_count` 范围合理（min < target < max）

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
3. 验证 injection 兼容性（执行上方检查清单）
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
| `injections.voice.source_sub_headings` | 从表达DNA section提取子节标题列表 |
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
1. 读取 `skills/story-style/{name}/meta.json`
2. 按 `meta.source_skill` 读取 `skills/story-style/{name}/SKILL.md`
3. 按 `meta.injections` 提取 section 注入 prompt
