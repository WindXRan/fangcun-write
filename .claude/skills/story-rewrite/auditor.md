# Auditor：33 维连续性审计

**LLM 驱动，零代码。读取章节 + truth files，输出结构化审计报告。**

---

## 触发方式

写完每章后自动触发，或手动 `/audit`

---

## 33 维度

| ID | 维度 | 说明 | 严重级 |
|----|------|------|--------|
| 1 | OOC检查 | 角色行为是否符合已建立的人设 | critical |
| 2 | 时间线检查 | 事件时间顺序是否矛盾 | critical |
| 3 | 设定冲突 | 世界观/设定是否自相矛盾 | critical |
| 4 | 战力崩坏 | 角色能力是否前后一致 | warning |
| 5 | 数值检查 | 金钱/距离/数量等数值是否矛盾 | warning |
| 6 | 伏笔检查 | 伏笔是否按计划铺设/回收 | critical |
| 7 | 节奏检查 | 最近3-5章是否形成完整周期 | warning |
| 8 | 文风检查 | 文风是否偏离风格锚点 | warning |
| 9 | 信息越界 | 角色是否知道不该知道的信息 | critical |
| 10 | 词汇疲劳 | 高频词/AI标记词密度 | warning |
| 11 | 利益链断裂 | 角色动机是否合理 | warning |
| 12 | 年代考据 | 历史/年代细节是否准确 | info |
| 13 | 配角降智 | 配角是否被弱化以衬托主角 | warning |
| 14 | 配角工具人化 | 配角是否只有功能性没有性格 | warning |
| 15 | 爽点虚化 | 爽点是否兑现了读者期待 | warning |
| 16 | 台词失真 | 对话是否符合角色身份/场景 | warning |
| 17 | 流水账 | 是否只是记流水账没有推进 | warning |
| 18 | 知识库污染 | truth files 是否被错误更新 | critical |
| 19 | 视角一致性 | POV 是否混乱跳切 | warning |
| 20 | 段落等长 | 段落长度变异系数是否过低 | info |
| 21 | 套话密度 | 模糊词/犹豫词密度 | info |
| 22 | 公式化转折 | 转折词是否重复使用 | info |
| 23 | 列表式结构 | 连续相同开头的句子 | info |
| 24 | 支线停滞 | 支线是否长期无推进 | warning |
| 25 | 弧线平坦 | 角色情绪弧线是否停滞 | warning |
| 26 | 节奏单调 | 章节类型是否连续重复 | warning |
| 27 | 敏感词检查 | 是否包含敏感内容 | critical |
| 28 | 正传事件冲突 | 番外是否与正传矛盾 | critical |
| 29 | 未来信息泄露 | 角色是否知道未来信息 | critical |
| 30 | 世界规则跨书一致性 | 跨书世界规则是否一致 | critical |
| 31 | 番外伏笔隔离 | 番外伏笔是否与正传混淆 | warning |
| 32 | 读者期待管理 | 读者期待是否被持续管理 | warning |
| 33 | 章节备忘偏离 | 正文是否偏离章节备忘 | critical |

---

## 审计 prompt 模板

```
你是连续性审计员。审阅以下章节，对照 truth files 检查 33 个维度。

## 章节正文
{chapter_content}

## Truth Files
### current_state.md
{current_state}

### pending_hooks.md
{pending_hooks}

### chapter_summaries.md
{chapter_summaries}

### character_matrix.md
{character_matrix}

### emotional_arcs.md
{emotional_arcs}

## 上一章正文（检查衔接）
{previous_chapter}

## 输出格式（JSON）
{
  "overall_score": 0-100,
  "passed": true/false,
  "issues": [
    {
      "dimension_id": 1,
      "dimension_name": "OOC检查",
      "severity": "critical/warning/info",
      "description": "具体问题描述",
      "location": "第X段/第X行",
      "suggestion": "修复建议"
    }
  ],
  "summary": "一句话审计结论"
}

## 评分校准
- 90-100：优秀，无 critical，warning ≤2
- 70-89：合格，无 critical，warning ≤5
- 50-69：需修改，有 critical 或 warning >5
- <50：打回重写

## 规则
- 你只审结构和连续性，不审文笔
- 文笔问题以 severity="info" 标注，不计入 passed 判定
- 每个维度最多报 2 个 issue
- 总 issue 数不超过 15 个
```

---

## 审计后流程

```
审计结果
├── passed=true（≥70分，无 critical）→ 通过，进入下一批
├── passed=true 但有 warning → 通过，warning 记录到上下文
└── passed=false（<70分或有 critical）→ 触发 reviser
```

---

## 与 rewrite 集成

在 story-rewrite 的 Step 4 校验中：

1. 先运行 `post_write_validator.py`（零 LLM，error 直接重写）
2. 通过后运行 auditor（LLM，33 维审计）
3. auditor passed → 通过
4. auditor failed → 运行 reviser（LLM，自动修订）
5. reviser 后重审 → 仍 failed → 标记 manual_required
