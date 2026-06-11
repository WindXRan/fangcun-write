---
name: story-trend
description: |
    热梗/题材调研工具。指定热点方向，自动搜索资料构建知识库，供开书阶段参考。
    触发条件：用户说「热梗调研」「搜热梗」「查题材」「构建知识库」「trend」「热点调研」。
    不要在用户只是问「怎么写」「帮我写大纲」时触发。
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(cp *) Bash(mkdir *) WebSearch WebFetch
shell: powershell
---

# story-trend（热梗调研 + 知识库构建）

> 指定热点题材 → 搜索资料 → 结构化知识库 → 注入开书

## 用途

仿写引擎的开书阶段需要"源文"做骨架，但**热度题材往往没有现成爆款源文**。
story-trend 解决这个问题：通过调研真实热点，构建素材知识库，让开书时有据可依。

## 信息源

| 来源 | 工具 | 内容 |
|------|------|------|
| 百度/网页 | WebSearch + WebFetch | 梗百科、新闻报道、知乎讨论 |
| **B站** | `tools/bilibili_search.py` | 切片视频、鬼畜、热评（第一手梗素材） |
| 番茄排行榜 | `story-scan` skill | 题材热度、竞品分析 |

## 流程

```
1. 用户指定热梗/题材方向（如"嘎子带货""AI觉醒""考公热"）
2. 网页搜索：梗百科、新闻、读者讨论
3. B站搜索：切片视频、鬼畜、热评（脚本自动执行）
4. 结构化整理到 trends/{题材名}/ 目录
5. 开书时通过 config 的 "trend_dir" 字段注入
```

## 文件结构

```
trends/{题材名}/
├── overview.md          # 题材概述：定义、爆点、读者画像
├── mechanics.md         # 核心机制：玩法/套路/反转模式
├── characters.md        # 角色模板：常见人设、反差组合
├── plot_patterns.md     # 情节模式：高频结构、爽点节奏
├── references.md        # 参考素材：真实案例、梗出处、热搜事件
├── bilibili_*.md        # B站搜索结果：视频列表+热评（脚本自动生成）
├── keywords.md          # 关键词/标签：读者搜索词、平台标签
└── style_notes.md       # 风格备注：适合的文风、语气、受众
```

## B站搜索工具

```bash
# 基本搜索
python .agents/skills/story-trend/tools/bilibili_search.py "嘎子带货" --limit 20 --comments 3

# 按播放量排序
python .agents/skills/story-trend/tools/bilibili_search.py "潘嘎之交" --limit 10 --sort click

# 按弹幕量排序（找最有梗的视频）
python .agents/skills/story-trend/tools/bilibili_search.py "嘎子偷狗" --limit 10 --sort dm

# 输出到文件
python .agents/skills/story-trend/tools/bilibili_search.py "嘎子带货" --limit 10 -o trends/嘎子带货/bilibili_嘎子带货.md
```

参数说明：
- `--limit`: 返回视频数量（默认20）
- `--order`: 排序方式 `totalrank`=综合 / `click`=播放 / `pubdate`=最新 / `dm`=弹幕 / `stow`=收藏
- `--comments`: 每个视频取几条热评（默认3，0=不取）
- `--output/-o`: 输出文件路径
- `--json`: 输出JSON格式

> ⚠️ B站API有频率限制，连续搜索时建议间隔2-3秒。被风控(-412)时脚本会自动重试。

## 使用方式

### 方式 1：交互式调研
```
用户：帮我调研"嘎子带货"这个题材
→ story-trend 执行搜索 + 整理
→ 输出到 trends/嘎子带货/
```

### 方式 2：pipeline 集成
```json
{
  "book_name": "过气童星的直播间",
  "source_book": "...",
  "trend_dir": "trends/嘎子带货",
  "api_key": null,
  "model": "deepseek-v4-flash"
}
```
开书时自动读取 trend_dir 下的素材作为参考。

### 方式 3：手动注入
开书 agent 读取 `trends/{题材名}/overview.md`，在设定时融入热度元素。

## 注意事项

- 知识库是**素材参考**，不是大纲。最终设定由开书阶段决定
- 搜索结果需要人工审核，去除不准确/过时的信息
- 热梗有时效性，建议调研后 1 周内使用
- 知识库内容会自然融入 plot_guide 和 write_chapter 的参考

## 配套 Skills

| Skill | 关系 | 说明 |
|-------|------|------|
| `story-engine` | 下游 | 开书时引用 trend_dir 的素材 |
| `story-scan` | 平行 | 番茄排行榜分析，可提供题材热度数据 |
| `story-blurb` | 下游 | 简介生成时可引用热梗关键词 |
