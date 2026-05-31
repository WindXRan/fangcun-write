# 编辑反馈结构化模板

> 编辑反馈后，按此模板填写，自动转化为规则变更。

## 基本信息

- **试水版本**：{commit hash 或版本号}
- **测试用例**：{sweet-pet / suspense-urban / period-family}
- **编辑评分**：{/100}
- **AI 痕迹**：{百分比}

## 问题分类（勾选）

### 表层问题（禁用词/句式类）
- [ ] 禁用词残留（列出：___）
- [ ] 句式套路（"不是A而是B"/"带着…"/"声音不大却…"）
- [ ] 章尾升华/总结
- [ ] 排比过多

### 风格问题（人格/语感类）
- [ ] 网络梗堆砌（列出高频词：___）
- [ ] 叙述者人格不一致
- [ ] 情绪表达千篇一律（列出重复表达：___）
- [ ] 第一人称混入
- [ ] 缺乏具体细节（抽象情绪多）

### 内容问题（逻辑/设定类）
- [ ] 设定逻辑不自洽（说明：___）
- [ ] 角色行为矛盾（说明：___）
- [ ] 情节推进不足

## 具体问题描述

| 位置 | 问题类型 | 原文 | 问题 | 建议修改 |
|------|----------|------|------|----------|
| 第X章第Y段 | | | | |

## 规则变更建议

根据以上问题，建议：
- [ ] 新增规则：___
- [ ] 修改规则：___
- [ ] 删除规则：___
- [ ] 调整 persona：___

## 自动转化映射

编辑反馈类型 → 需要修改的文件：

| 反馈类型 | 修改文件 | 修改位置 |
|----------|----------|----------|
| 禁用词残留 | `skills/story-deslop/references/banned-words.md` | 添加新词 |
| 古早梗 | `skills/_shared/agents/narrative-writer.md` | "禁用古早梗"段落 |
| 人设崩了 | `skills/_shared/agents/narrative-writer.md` | "人设一致性"段落 |
| 叙述者消失 | `skills/_shared/agents/narrative-writer.md` | "正确示范"段落 |
| 网络梗堆砌 | `skills/story-rewrite/references/narrator-persona.md` | 对应人格类型的"语言特征" |
| 语感样本重复 | `skills/story-rewrite/references/narrator-persona.md` | "实际仿写时"说明 |
| 段落太均匀 | `skills/_shared/agents/narrative-writer.md` | "自检2"段落 |
| 情绪重复 | `skills/_shared/agents/narrative-writer.md` | "反AI补丁"段落 |

修改后运行验证：
```powershell
python skills/story-rewrite/tools/validate-aigc.ps1 -Path '<文件>'
python skills/story-rewrite/tools/check-consistency.py '<文件>'
```
