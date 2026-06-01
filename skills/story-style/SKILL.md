---
name: story-style
description: |
  写作风格过渡层。连接女娲（上游）和 story-rewrite（下游），提供风格发现与路径查询。
  触发方式：/story-style、/文风、「有什么风格」「风格列表」「用XX风格写」
---

# story-style：写作风格过渡层

> 连接上游（nuwa 蒸馏产出）和下游（story-rewrite 消费），中间不做加工。

## 核心职责

| 职责 | 说明 |
|------|------|
| **发现** | 扫描目录，找到所有可用风格的 SKILL.md |
| **查询** | `--style={name}` → 返回 SKILL.md 路径 |
| **验证** | 检查 SKILL.md 是否包含必要 section |

**不做的事**：不提取 injection、不生成 meta.json、不加工 SKILL.md 内容。agent 直接读原文。

---

## 风格发现

扫描两个位置，合并为统一注册表：

| 位置 | 来源 | 示例 |
|------|------|------|
| `skills/story-style/*/SKILL.md` | 网文作者文风（nuwa 网文模式产出） | `skills/story-style/wenqi/SKILL.md` |
| `.claude/skills/*-perspective/SKILL.md` | 通用人物 Skill（nuwa 通用模式产出） | `.claude/skills/munger-perspective/SKILL.md` |

**注册规则**：目录下存在 `SKILL.md` → 注册为可用风格。不需要 meta.json。

**名称映射**：
- `skills/story-style/{name}/SKILL.md` → 风格名 = `{name}`
- `.claude/skills/{name}-perspective/SKILL.md` → 风格名 = `{name}`

---

## 风格查询

`story-rewrite` 发起 `--style={name}` 请求时：

1. 查 `skills/story-style/{name}/SKILL.md` → 存在则返回路径
2. 不存在 → 查 `.claude/skills/{name}-perspective/SKILL.md` → 存在则返回路径
3. 都不存在 → 报错：「风格 {name} 未找到」

story-rewrite 拿到路径后，agent 直接 read SKILL.md 获取完整风格信息。

---

## 验证

### 风格质量基线

| 维度 | 最低标准 | 说明 |
|------|---------|------|
| **表达DNA** | ≥5个量化特征 | 句式、转折词、动词、口癖、章节模式 |
| **写作心智模型** | ≥3个 | 如开篇结构、糖点密度、结尾钩子 |
| **章纲模板** | 必须有 | 感情线/剧情线骨架 |
| **质量检查清单** | 必须有 | 黄金三章自查、写作过程自查等 |

**质量评级**：

| 评级 | 标准 | 可用场景 |
|------|------|---------|
| ⭐⭐⭐ | 满足所有基线 + 有全量统计 + 有章纲模板 | story-rewrite 全功能 |
| ⭐⭐ | 满足基线 + 有章纲模板 | story-rewrite 基本功能 |
| ⭐ | 满足基线 | story-rewrite 降级模式 |
| ❌ | 不满足基线 | 不可用于 story-rewrite |

---

## 上下游衔接

```
nuwa（上游，原版不动）
  │
  ├─ 通用人物 → .claude/skills/{name}-perspective/SKILL.md
  │
  └─ 网文作者 → skills/story-style/{name}/SKILL.md
          │
          ↓
story-style（本层，过渡层）
  │
  ├─ 发现：扫描两个目录
  ├─ 查询：--style={name} → 返回路径
  └─ 验证：检查 SKILL.md 质量基线
          │
          ↓
story-rewrite（下游，消费风格）
  │
  └─ read SKILL.md → 获取表达DNA/章纲模板/钩子类型等
```

---

## 使用方式

```
# 查看可用风格
/story-style

# 验证某个风格是否可用
/story-style --validate=wenqi

# 路由到 story-rewrite，加载闻栖风格写全书
/story-rewrite --style=wenqi
```
