---
name: fangcun-write
version: 7.0.0
description: |
  方寸仿写引擎。严格工作流合约，禁止跳过任何步骤。
---

# 方寸工作流合约

**以下规则为硬约束，禁止违反。**

---

## 写第N章：三纲法，缺一不可

```
Step 0: 确定卷位置
  → 查看 正文/卷纲/ 确定第N章属于第几卷
  → 读对应卷的卷纲，了解本章在卷弧线中的位置
  → 如果卷纲不存在 → 先建卷纲，再写章

Step 1: preflight
  → quality_checker.py check --chapter N
  → exit code != 0 时禁止继续

Step 2: 源文章纲提取（不允许手动编写章纲）
  → source-guide-reverse 从源文正文提取结构
  → 输出到源文项目 正文/章纲/第N章.xml

Step 3: 章纲转换（不允许直接使用源文章纲）
  → guide-convert 将源文章纲转换为仿写章纲
  → 输出到仿写项目 正文/章纲/第N章.xml
  → 检查 tool 属性必须为 "guide-convert"

Step 4: 写正文（不允许手动编写正文）
  → write-chapter 按仿写章纲写正文
  → 输出到仿写项目 正文/正文/第N章.xml

Step 5: 审查修复
  → fanxie-review（读者视角审查）
  → fanxie-structural-fix（如结构偏离章纲）
  → fanxie-fix（如技法偏差）

Step 6: 质量门禁
  → quality_checker.py audit project_dir
  → exit code != 0 时阻塞，必须修复到通过

Step 7: 展示前500字+尾200字给用户确认
  → 用户说"可以"才进入下一章
```

## 禁止事项（违反视同违约）

```
❌ 禁止手动编写章纲（必须用 source-guide-reverse）
❌ 禁止直接使用源文章纲（必须用 guide-convert 转换）
❌ 禁止手动编写正文（必须用 write-chapter）
❌ 禁止跳过 quality_checker
❌ 禁止跳过用户确认直接下一章
❌ 禁止在仿写中添加源文没有的背景/情节/人物内心
❌ 禁止缩写或扩写源文的信息释放节奏
🔴 禁止洗稿：同一功能不能用和源文相同的句式/措辞/修辞
   ➜ 源文写"主角投胎了。她刚刚被分娩出来，就奋力睁大了眼睛"
   ➜ 洗稿："仿写主角投胎了。她刚刚被分娩出来，就奋力睁大了眼睛" ❌
   ➜ 仿写："仿写主角努力撑开黏糊糊的眼皮，入目是一室烛光" ✅
   ➜ 功能相同（分娩睁眼+环境），措辞完全不同
```

## 允许事项

```
✅ 角色名/称谓/势力名/地名/时代背景的换皮
✅ 保留源文的情绪弧线和信息释放点（必须一致）
✅ 保留源文的节奏密度（段落数、OS密度、对话比例）
✅ 用不同的语言表达相同的情节功能（这才是仿写）
```

## 质量门禁

```bash
# 写前检查（阻塞）
python quality_checker.py check project_dir --chapter N

# 写后审计（阻塞）
python quality_checker.py audit project_dir
```

`exit code 0` = 通过。`exit code 1` = 阻塞，必须先修复。

---

## 参考：工具清单

| 工具 | 必用？ | 触发条件 |
|------|:------:|---------|
| source-guide-reverse | ✅ 必用 | 每章一次，读源文出章纲 |
| guide-convert | ✅ 必用 | 每章一次，源文章纲→仿写章纲 |
| write-chapter | ✅ 必用 | 有仿写章纲后写正文 |
| quality_checker.py | ✅ 必用 | 写前+写后两次 |
| fanxie-review | ✅ 必用 | 写完后审查 |
| fanxie-structural-fix | ⚠️ 需要时 | 结构偏离章纲时 |
| fanxie-fix | ⚠️ 需要时 | 技法偏差时 |
| character-split | ⚠️ 需要时 | 存在复合角色时 |
| 开书脑洞/开书评估 | 📋 开书阶段 | 新项目启动时 |
| world-mapper | 📋 开书阶段 | 开书评估通过后 |
