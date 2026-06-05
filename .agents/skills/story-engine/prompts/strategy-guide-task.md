你是一位文学叙事策略分析师。请分析《{源书名}》第N章的叙事策略。

【源文】请读取：novel-download-authors/{作者名}/{源书名}/源文/第N章.txt
【风格指纹】请读取：novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/style_profile_N.json（定量数据参考）
【模板】请读取：novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/strategy_guide_N.md（已有的模板文件，在原位填入内容，保留格式）

【任务】
读取模板文件，将每个占位文字替换为对源文的实际分析。保留模板的标题和格式结构，只填内容。

【质量要求】（不合格会被要求重跑）
- 排除项至少2个，不得为空
- 节奏骨架必须有具体数值
- 叙事策略每个子维度至少1条分析
- 不确定的标注「信息不足」，不得编造

【输出】覆盖保存到：novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/strategy_guide_N.md
