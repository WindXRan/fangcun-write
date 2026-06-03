# Reviser：自动修订

**LLM 驱动。读取审计报告 + 原文，输出修订版。**

---

## 触发方式

审计 failed 时自动触发，或手动 `/revise`

---

## 修订 prompt 模板

```
你是修订者。根据审计报告修订章节正文。

## 原文
{original_chapter}

## 审计报告
{audit_report}

## Truth Files（修订后必须保持一致）
{truth_files_summary}

## 修订规则

1. 只修复审计报告中标记为 critical 和 warning 的 issue
2. info 级别的 issue 可选择性修复
3. 修订后的内容必须与 truth files 保持一致
4. 不能引入新的 OOC、时间线矛盾、设定冲突
5. 保持原文的字数范围（±20%）
6. 保持原文的情绪基调和节奏
7. 保留原文的伏笔铺设

## 输出格式

输出修订后的完整章节正文，直接写入文件。

## 修订模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| spot-fix | 定点修复，只改有问题的段落 | issue ≤3 个，且都是局部问题 |
| rewrite | 重写整个章节 | issue >3 个，或有结构性问题 |
| anti-detect | 反检测修订 | AI 痕迹过重时 |

默认使用 spot-fix。issue >3 个时自动升级为 rewrite。
```

---

## 修订后流程

```
修订完成
├── 重跑 post_write_validator.py（零 LLM）
│   ├── error → 再修订一次
│   └── pass → ②
├── 重跑 auditor（LLM）
│   ├── passed → 通过
│   └── failed → 标记 manual_required，不再自动修订
└── 更新 truth files（Observer）
```

---

## 修订次数限制

- 每章最多自动修订 **1 次**
- 修订后仍 failed → 标记 `manual_required`
- 连续 3 章 manual_required → 暂停，等待人工介入

---

## 与 rewrite 集成

在 story-rewrite 的 Step 4 校验中：

```
Step 4：校验
  ① post_write_validator.py（零 LLM）
     error → 直接重写（不走修订，直接重写整章）
     pass → ②
  ② auditor（LLM，33 维）
     passed → 通过
     failed → ③
  ③ reviser（LLM，自动修订）
     spot-fix/rewrite → ④
  ④ 重跑 auditor
     passed → 通过
     failed → manual_required
```
