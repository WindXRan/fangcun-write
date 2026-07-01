# 正文写作管线

**目标：** 按章纲写一章正文，过格式和AI腔检查
**前提：** `outline-build` 管线已完成，当前章有章纲
**循环：** 每章跑一轮，192 章跑 192 轮
**入口：** `run_tool("工具名", {参数}, project_dir)`

---

## 原创模式每章步骤

```
Step 1: 写正文 → 展示给用户 → 确认? → 不满意回炉 → 满意进下一步
Step 2: 去AI味 → 展示给用户 → 确认? → 不满意回炉 → 满意进下一步
Step 3: 对比审查 → 展示给用户 → 确认? → 不满意回炉 → 下一章
```

---

## 仿写模式自动化管线（Pattern-First — 全自动联调）

### 建书阶段（一次执行 — **每一步都需用户确认**）

```
Step A: 仿写开书（需用户确认）
    run_tool("open-book", {story_name: "新书"}, project_dir)
    → 读取源文第1章 → 生成总纲/简介/标签/角色/设定/卷纲（~12文件）
    ⚠️ 展示总纲+角色名+设定给用户确认
        用户确认题材/人设/世界观方向后再继续

Step B: 卷纲验证（需用户确认）
    run_tool("volume-outline", {}, project_dir)
    → 独立的卷纲生成，检查开书产出的卷纲质量
    ⚠️ 展示卷纲的arc列表给用户确认
        确认节奏和剧情走向后再进入每章写作
```

### 每章自动化流水线

```
Step 1: 章纲（读源文结构，对齐信息释放节奏）
    run_tool("plot-guide", {chapter_number: N}, project_dir)
    → 读源文 info_release 节奏
    → 生成五段式细纲，每个beat标注源文对标位置

Step 2: 仿写写章（含自动字数压缩）
    run_tool("fanxie-chapter", {chapter_number: N}, project_dir)
    → 读章纲 + 总纲 + 角色卡 + 设定 → 写正文
    → 自动检查字数，超3000字自动压缩
    → 展示给用户确认

Step 4: 对齐审查
    run_tool("fanxie-review", {chapter_number: N}, project_dir)
    → 以章纲为基准审查 D1-D5
    → 展示诊断报告

Step 5: 如有问题 → 自动靶向修复
    run_tool("fanxie-fix", {chapter_number: N, user_input: 报告}, project_dir)
    → 读章纲 + 审查报告，只修有问题的维度
    → 展示修改对比

Step 6: 去AI味
    run_tool("deslop", {chapter_number: N}, project_dir)
    → 展示修改对比

每5章：fanxie-prompt-opt → 聚合失败模式 → 优化prompt

### 质量增强步骤（可选，按需调用）

```
首章/改逆推prompt后：
  Step V1: 盲区检测
      run_tool("fanxie-blindspot", {chapter_number: N}, project_dir)
      → 原文→章纲对比 → 找出逆推遗漏的关键要素 → 修 source-guide-reverse
      → 展示盲区报告

  Step V2: 章纲逆推质量验证
      run_tool("source-guide-reverse-validate", {chapter_number: N}, project_dir)
      → 检查章纲完整性/一致性/结构准确/泛化能力
      → 展示验证报告

跨轮次优化（每次 Round 前后）：
  Round前：读 _optimize/anomaly_patterns.md → 优先修 active 最久的模式
  Round后：更新 _optimize/anomaly_patterns.md → 跟踪复现/休眠/解决
  同一模式连续 ≥2 轮复现 → 启动升版修复方案
```

---

## Step 1: 写正文

```
run_tool("write-chapter", {"chapter_number": N}, project_dir)
```

**自动注入的上下文（不需要手动传）：**

| 变量 | 来源 | 内容 |
|------|------|------|
| `@作品信息/主题/总纲` | 文件读取 | 全书总纲 |
| `@正文/章纲/第N章.xml` | 文件读取 | 本章章纲（情绪弧线+情节点） |
| `@关联章节` | computed handler | 上一章最后 500 字 |
| `@关联章纲` | computed handler | 前 3 章章纲 |
| `@关联角色` | computed handler | 章纲 <characters> 对应的角色卡 |
| `@目标频道` | project.xml | 男频/女频 |
| `@目标字数` | computed handler | 基于源文估算 |
| `@前文章纲` | 用户输入（可选） | 额外前文参考 |

**输出格式：**
```
==== 正文/正文/第N章.xml ====
<chapter number="N">
  <content>
（正文内容，不写章节标题、不写分隔线）
  </content>
</chapter>
```

**展示→确认：**
- 展示正文前 500 字 + 末尾 200 字
- 问："满意吗？[Y/重改理由/跳过]"
- Y → 下一步
- 重改 → 收集反馈重新生成
- 跳过 → 进下一步（保留当前版本）

---

## Step 2: 去AI味

```
run_tool("deslop", {"chapter_number": N}, project_dir)
```

**检查项：**
- 禁止万能比喻（"像潮水般""如闪电般"）
- 禁止「他感到」「他觉得」「他意识到」直述情绪
- 禁止「他说」「她道」对话标签
- 禁止章末总结升华
- 禁止连续 3 段以上纯描写
- 禁止连续 2 段以上纯心理活动
- 禁止所有角色说话方式一样

**展示→确认：** 展示修改前后对比（重点标红修改处）

---

## Step 3: 对比审查

```
run_tool("compare", {
  "user_input": "审查第N章",
  "chapter_number": N
}, project_dir)
```

**审查维度：**
- 章纲对齐度：情绪弧线是否匹配、情节点是否覆盖
- 格式规范：空行/主语密集/视角跳出/描叙比例
- 角色匹配：对话方式是否符合语言档案
- 字数：是否在目标范围内

**展示→确认：** 展示审查报告（通过/问题列表）
- 全部通过 → 下一章
- 有问题 → 修复指定项后重新生成

---

## 写作红线（逐条遵守）

```
格式：
- 不写章节标题、不写分隔线
- 段落按戏剧单元自然断开，不机械分段
- 段落间不空行（只一个 \n）
- 对话独立成行，用动作引出，不用「他说」「她道」

视角：
- 限知第三人称，不跳其他角色内心
- 读者只能知道主角看到、听到、感觉到的东西

情绪：
- 还原章纲的情绪弧线
- 用身体反应展示情绪（"手心出汗" > "他很紧张"）
- 不用章末总结升华

描写：
- 穿插在动作和对话中，不连续超过 3 段纯描写
- 不用万能比喻

对话：
- 每段对话必须有功能（推进情节/制造期待/传递情绪）
- 角色说话方式符合语言档案
- 不写解释性对话
```
