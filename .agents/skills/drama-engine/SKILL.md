---
name: drama-engine
version: 2.1.0
description: |
  小说转短剧剧本引擎。基于 Toonflow 原生 3 阶段 pipeline：故事骨架 → 改编策略 → 剧本编写。
  包含事件提取、质量审核、合并导出完整流程。
  触发方式：/drama-engine、/剧本、「小说转剧本」「帮我写剧本」「改编短剧」
---

# drama-engine：小说转短剧剧本引擎

基于 Toonflow 原生流程的 3 阶段短剧改编系统。将小说原文通过事件提取 → 故事骨架 → 改编策略 → 剧本编写的完整 pipeline，输出标准短剧剧本。

## 核心流程

```
小说原文 → 事件提取 → 故事骨架 → 审核骨架 → 改编策略 → 审核策略 → 剧本编写 → 导出
  (Phase)    event     skeleton   review    adaptation   review    script    export
```

审核前置：骨架/策略产出后立即审核，不通过则修正后再进入下一阶段。避免基于错误骨架写剧本。

## 用法

```bash
# 完整流程（骨架→审核→改编→审核→剧本→导出）
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json

# 分步执行
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase event       # 事件提取
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase skeleton    # 故事骨架
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase review --review-target skeleton  # 审核骨架
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase adaptation  # 改编策略
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase review --review-target adaptation  # 审核策略
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase script --start 1 --end 10  # 剧本编写
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase review      # 质量审核
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase export      # 合并导出

# 断点续传（自动从上次中断的地方继续）
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase resume

# 查看进度
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase status

# 调试模式
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --dry-run
```

## 配置文件

```json
{
  "novel_name": "原著书名",
  "drama_name": "剧本名",
  "source_dir": "projects/作者/书名/_cache/chapters",
  "output_dir": "projects/作者/书名/drama",
  "api_key": null,
  "api_base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "model_overrides": {
    "event": "deepseek-chat",
    "skeleton": "mimo-v2.5-pro",
    "adaptation": "mimo-v2.5-pro",
    "script": "mimo-v2.5-pro",
    "review": "mimo-v2.5-pro"
  },
  "project": {
    "episodes": 30,
    "episode_duration": 2,
    "chapter_range": [1, 153],
    "platform": "竖屏9:16",
    "style": "甜宠喜剧",
    "paywall": "前3集免费，第4集起付费"
  }
}
```

### 按阶段配置模型（model_overrides）

不同阶段可以用不同模型：

| 阶段 | 推荐模型 | 原因 |
|------|----------|------|
| event | `deepseek-chat`（非推理） | 事件提取简单任务，不需要深度推理，推理模型会浪费 token |
| skeleton | `mimo-v2.5-pro` | 需要强推理能力规划全局结构 |
| adaptation | `mimo-v2.5-pro` | 需要理解能力制定策略 |
| script | `mimo-v2.5-pro` | 需要创意写作能力 |
| review | `mimo-v2.5-pro` | 需要分析能力 |

> 事件提取未配置 `model_overrides` 时默认用 `deepseek-chat`，避免推理 token 浪费。

> `api_key` 为 null 时从 `$env:API_KEY` 读取。不要将 key 写入配置文件。

## 输出目录结构

```
projects/{作者}/{书名}/drama/
├── state.json               # 进度状态（断点续传）
├── events.json              # 事件表（增量保存，中断不丢数据）
├── story_skeleton.md        # 故事骨架
├── adaptation_strategy.md   # 改编策略
├── scripts/
│   ├── ep_001.txt           # 单集剧本
│   └── ...
├── reviews/
│   ├── skeleton_review.md   # 骨架审核报告
│   └── adaptation_review.md # 策略审核报告
└── {drama_name}.txt         # 合并导出
```

## 优化项

### 1. 断点续传（state.json）

每个 phase 开始/完成/失败都记录到 state.json。中断后用 `--phase resume` 自动从断点继续。
- `--phase status` 查看当前进度
- `--phase resume` 从上次中断的 phase 继续
- 已完成的 phase 自动跳过

### 2. 事件提取滑窗上下文

每章提取时自动带前 2 章的事件摘要作为上下文，保持角色名和情节一致性。

### 3. 增量保存

事件提取每完成一章立即写入文件。中断后重跑自动跳过已有章节。

### 4. 增量骨架

当事件表不完整时（如只有 21/153 章），骨架只为有事件支撑的章节规划集数，未覆盖章节标记"待补充"，不会凭空推测。

### 5. 剧本骨架片段提取

每集剧本只传当前集相关的骨架信息（故事核 + 当前集分集 + 所属幕），不传全量骨架，避免 context 爆炸。

### 6. 输出校验

剧本生成后自动校验：
- △ 场景描述标记（≥3 处）
- 字数范围（目标 ±50%）
- XML 标签完整性
- 场景标题格式
- 转场标注
- 单句台词长度（>25 字警告）

校验结果在终端显示 ⚠ 标记，不阻断流程。

## 3 阶段 Pipeline 详解

### Phase 1: 故事骨架（skeleton）

基于事件表构建故事骨架，包含：
- **故事核**：一句话核心吸引力 + 心理级爽点 + 金手指及约束
- **隐线**：主角内在成长轨迹（人物弧）
- **人物小传**：大三角核心角色 ≤4 人
- **三幕结构**：每幕功能、核心问题、幕末转折
- **分集决策**：逐集展开（≤20集）或总览+关键集展开（>20集）
- **付费卡点设计**：按 ≈10%/30%/50%/70%/90% 比例分布
- **股价级反转登记表**：全剧 ≈3 个反转

### Phase 2: 改编策略（adaptation）

基于骨架制定改编策略，包含：
- **核心改编原则**（3-5条）：正面指导 + 负面边界
- **主要删除决策**：删/压缩内容 + 原因 + 替代方案
- **世界观呈现策略**：出场节奏 + 解释度 + 锚点角色

### Phase 3: 剧本编写（script）

逐集编写剧本，格式：
- `<scriptItem name="...">` XML 包裹
- △场景描述（可直接用于 AI 视频生成）
- OS/V.S. 旁白标注
- 标准转场标注（硬切/淡入/闪白/闪黑/叠化）

### Phase 4: 质量审核（review）

对照审核维度逐项检查：
- **骨架审核**：14 项审核维度
- **策略审核**：14 项审核维度
- **评分体系**：A / B / C / D

## Prompt 文件

| 文件 | 用途 |
|------|------|
| `prompts/event_extraction.md` | 事件提取（单章 → 结构化事件行） |
| `prompts/decision.md` | 决策层逻辑（项目初始化 + 流水线调度） |
| `prompts/skeleton.md` | 故事骨架搭建（短剧爆款方法论） |
| `prompts/adaptation.md` | 改编策略制定（8大要点 + 删减决策） |
| `prompts/script.md` | 剧本编写（△格式 + 三大密度 + 节奏3-15-45） |
| `prompts/supervision.md` | 质量审核（红线清单 + 评分体系） |
