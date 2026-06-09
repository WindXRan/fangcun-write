---
name: story-optimize
description: |
    根据审稿反馈或对比报告，自动优化prompt。
    触发条件：用户说「优化prompt」「根据审稿优化」「prompt不好使」。
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(cp *) Bash(mkdir *)
shell: powershell
---

# story-optimize（prompt优化器）

> 根据审稿反馈或对比报告，自动分析问题并优化prompt。

## 流程

```
输入：审稿反馈 / 对比报告 / 用户描述的问题
↓
分析：定位问题属于哪个prompt（open-book/plot-guide/style-guide/write-chapter）
↓
优化：修改对应prompt，强化规则
↓
验证：跑3章测试效果
```

## 问题分类

| 问题类型 | 对应prompt | 优化方向 |
|---------|-----------|---------|
| 开篇无吸引力 | open-book | 强化简介要求、第一章钩子 |
| 节奏太慢 | plot-guide | 禁止纯日常、每章必须有冲突 |
| 人设无记忆点 | plot-guide | 男主钩子人设、女主主动性 |
| 撞梗/抄袭风险 | plot-guide | 换皮检验、桥段检查 |
| 省略号/AI味太多 | style-guide | 防AI检测规则 |
| 字数偏差大 | style-guide | 字数控制规则 |
| 人名不对 | rewrite_chapters | 角色名注入逻辑 |
| 简介质量差 | open-book | 简介结构要求 |

## 使用方式

用户说「优化prompt」时：
1. 读取最近的审稿反馈或对比报告
2. 分析问题属于哪个prompt
3. 修改对应prompt
4. 跑3章验证效果
5. 如果效果不好，继续优化

## 输出

修改对应的prompt文件，并提交到git。
