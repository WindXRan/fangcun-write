---
name: fangcun-drama
description: |
  小说转短剧剧本引擎。基于 Toonflow 原生 3 阶段 pipeline：故事骨架 → 改编策略 → 剧本编写。
  触发方式：「写剧本」「改编短剧」「小说转剧本」「帮我写剧本」
allowed-tools: Bash(python *)
---

# fangcun-drama：短剧剧本引擎

## 你是 agent，负责：

1. **理解用户意图**（"把这本书改成短剧" → 跑全流程）
2. **组装正确的命令**
3. **检查输出质量**（剧本格式、字数、角色名）
4. **处理错误**

## 流程

```
event → skeleton → skeleton_review → adaptation → adaptation_review → script → export
```

审核前置：骨架/策略产出后立即审核，不通过则修正后再进入下一阶段。

```bash
# 全流程
python .agents/skills/fangcun-drama/tools/pipeline.py --config {config}

# 分步执行
python .agents/skills/fangcun-drama/tools/pipeline.py --config {config} --phase event
python .agents/skills/fangcun-drama/tools/pipeline.py --config {config} --phase skeleton
python .agents/skills/fangcun-drama/tools/pipeline.py --config {config} --phase review --review-target skeleton
python .agents/skills/fangcun-drama/tools/pipeline.py --config {config} --phase adaptation
python .agents/skills/fangcun-drama/tools/pipeline.py --config {config} --phase review --review-target adaptation
python .agents/skills/fangcun-drama/tools/pipeline.py --config {config} --phase script --start 1 --end 10
python .agents/skills/fangcun-drama/tools/pipeline.py --config {config} --phase export

# 断点续传
python .agents/skills/fangcun-drama/tools/pipeline.py --config {config} --phase resume

# 查看进度
python .agents/skills/fangcun-drama/tools/pipeline.py --config {config} --phase status
```

## 配置文件

```json
{
  "novel_name": "原著书名",
  "drama_name": "剧本名",
  "source_dir": "projects/作者/书名/_cache/chapters",
  "output_dir": "projects/作者/书名/drama",
  "api_key": "sk-xxx",
  "api_base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "model_overrides": {
    "event": "deepseek-chat"
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

## 输出格式

剧本使用 `<scriptItem>` XML 标签包裹，△ 标记场景描述。

## 剧本结构核心原则（专业编剧规范）

### 1. 四个卡点
卡点为观众付费点，可以理解为网文当中的上架，因此，卡点十分关键，必须牢牢抓住观众情绪。
- 每一个卡点都要在前一个卡点的基础上递进十集
- 一卡为整部剧本最为重要的卡点（最好在第十集进行卡点）
- 卡点位置：约10%/30%/50%/70%/90%

### 2. 多次反转
尽量在剧集中多融入反转内容：
- 基于逻辑人设的有效反转，不能空穴来风
- 不能忽视逻辑
- 反转要有看点，要有强烈的期待感
- 要能抓住观众的眼球

### 3. 期待不断
开篇融入期待感，后续保持期待不断：
- 尽量围绕着期待去展开剧情
- 期待感和主线要互相融合，你中有我，我中有你
- 千万不能让期待感和主线产生分歧

### 4. 主线情绪
剧情围绕主线，不要东一下西一下：
- 尽量少开支线
- 要跟着主线去推动人物
- 以主线作为核心去塑造整体剧情

### 5. 框架写作
短剧的创作，不是空穴来风，头脑风暴，拿笔随手写出来的，而是需要方法论的支持：
- 需要一个框架来作为底层的创作逻辑
- 其余的人物，剧情，亦或者其他细枝末节的东西，只不过在这个框架上去进行填充
- 框架可以简单理解为：爆款短剧的底层逻辑
- 也就是：节奏的安排，爽点的布置，主线的期待
- 将这些点作为框架，再把其余的新东西填充进去

## 质量检查（agent 自动执行）

跑完后 agent 应该：
1. 读 `scripts/ep_001.txt`，检查格式是否正确（△标记、场景标题、台词）
2. 检查字数是否在 2000-3000
3. 检查角色名是否正确
4. 读 `reviews/` 目录，汇报审核评分
5. 如有问题，告诉用户

## 常见场景

| 用户说 | agent 做 |
|--------|----------|
| "把这本书改成短剧" | 配置参数 → 跑全流程 |
| "写前10集剧本" | 跑 --phase script --start 1 --end 10 |
| "继续写" | 跑 --phase resume |
| "看看剧本质量" | 读 scripts/ → 跑 --phase review |
| "骨架有问题" | 跑 --phase skeleton（覆盖旧的）→ 跑 --phase review |
