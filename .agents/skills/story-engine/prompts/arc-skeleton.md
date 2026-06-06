请为《{新书名}》设计开书产出。

【源文总章数】{N}章
【源文参考】novel-download-authors/{作者名}/{源书名}.txt（合并文件，开头含书名/作者/分类/标签/简介，后接全部章节）
- 读开头部分：提取书名、分类、标签、简介，了解故事类型
- 读结尾部分：了解结局基调

【任务】
按顺序启动 2 个子 agent：

1. **Agent A1：新书设定**（必须先完成）
   - Task prompt：prompts/arc-concept.md
   - 输出：仿写/{新书名}/设定/新书设定.md + 仿写/{新书名}/设定/简介.md

2. **Agent A2：全书弧线**（等 A1 完成后启动）
   - Task prompt：prompts/arc-skeleton-core.md
   - 输出：仿写/{新书名}/设定/全书弧线.md
