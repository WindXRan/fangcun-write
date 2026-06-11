调研题材「{题材名}」，构建知识库。

---

## 任务

针对用户指定的热点题材/梗，通过搜索收集素材，整理为结构化知识库。

## 调研维度

### 1. 题材定义（overview.md）
- 这个题材/梗是什么？一句话定义
- 核心爆点是什么？读者为什么爱看？
- 目标读者画像（年龄/性别/阅读偏好）
- 在番茄/起点/抖音的热度表现
- 代表作品（如果有的话）

### 2. 核心机制（mechanics.md）
- 这个题材的"爽点循环"是什么？
- 常见的反转模式有哪些？
- 读者期待的"名场面"有哪些？
- 节奏特点（快热还是慢热？单线还是多线？）

### 3. 角色模板（characters.md）
- 这类题材常见的主角类型
- 经典的反差组合（如：落魄大佬×小白）
- 配角功能型角色（如：损友、黑粉、铁粉）
- 人设创新空间（怎么在套路里出新意）

### 4. 情节模式（plot_patterns.md）
- 高频使用的故事结构
- 爽点分布节奏（几章一小爽，几章一大爽）
- 常见的冲突类型
- 禁忌/雷区（读者最讨厌什么）

### 5. 参考素材（references.md）
- 真实案例/新闻事件（增加真实感）
- 梗的出处和演变
- 相关热搜/话题
- 可借鉴的细节（行业黑话、内部梗）

### 6. B站切片/鬼畜素材（bilibili_*.md）
- **必须执行**：用 B站搜索脚本收集相关视频
- 搜索关键词组合：题材名、核心梗、衍生梗（至少搜3组关键词）
- 按播放量排序，取 Top 20 视频的标题、UP主、播放量、热评
- 重点关注：鬼畜视频（素材最密集）、切片视频（名场面出处）、吐槽/分析视频（观点提炼）
- 热评 = 第一手用户态度，直接反映读者情绪

```bash
# B站搜索（每个关键词单独搜）
python .agents/skills/story-trend/tools/bilibili_search.py "嘎子带货" --limit 10 --order click --comments 3 --output trends/嘎子带货/bilibili_嘎子带货.md
python .agents/skills/story-trend/tools/bilibili_search.py "潘嘎之交" --limit 10 --order click --comments 3 --output trends/嘎子带货/bilibili_潘嘎之交.md
python .agents/skills/story-trend/tools/bilibili_search.py "嘎子偷狗" --limit 10 --order dm --comments 3 --output trends/嘎子带货/bilibili_嘎子偷狗.md
```

### 7. 关键词（keywords.md）
- 读者搜索词（番茄/起点搜索框）
- 平台标签/分类
- 热门短语/口号
- 章节标题常用词

### 8. 风格备注（style_notes.md）
- 适合的文风（轻松/严肃/沙雕/热血）
- 对话风格（网络用语/方言/行业术语）
- 叙事视角推荐（第一人称/第三人称）
- 特殊写作技巧（如：弹幕体、直播体、评论区体）

---

## 输出

用 `===FILE: 路径===` 分隔符输出多个文件到 `trends/{题材名}/` 目录。

===FILE: trends/{题材名}/overview.md===

===FILE: trends/{题材名}/mechanics.md===

===FILE: trends/{题材名}/characters.md===

===FILE: trends/{题材名}/plot_patterns.md===

===FILE: trends/{题材名}/references.md===

===FILE: trends/{题材名}/keywords.md===

===FILE: trends/{题材名}/style_notes.md===

（B站搜索结果由脚本自动保存到 trends/{题材名}/bilibili_*.md，不需要在这里输出）
