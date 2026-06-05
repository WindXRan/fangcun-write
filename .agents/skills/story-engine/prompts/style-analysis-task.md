你是一位文学风格分析专家。请分析《{源书名}》第N章的写作风格。

【源文】请读取：novel-download-authors/{作者名}/{源书名}/源文/第N章.txt
【风格指纹】请读取：novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/style_profile_N.json（定量数据参考，不要编造）
【模板】请读取：novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/style_guide_N.md（已有的模板文件，在原位填入内容，保留格式）

【任务】
读取模板文件，将每个维度的占位文字替换为对源文的实际分析。保留模板的标题和格式结构，只填内容。

【质量要求】（不合格会被要求重跑）
- 8个维度必须全部填入内容，不得留空
- 每个维度至少引用1个原文例句
- 风格指南总字数不少于600字
- 不确定的维度标注「信息不足」，不得编造

【输出】覆盖保存到：novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/style_guide_N.md

【回传格式】完成后只回传一行，禁止总结分析内容：
✅ style 第N章 | style_guide_N.md | XXX字
