从《{源书名}》所有章节提取写作指纹，纯脚本批量生成，不走LLM。

【源文目录】novel-download-authors/{作者名}/{源书名}/源文/
【输出目录】novel-download-authors/{作者名}/{源书名}/蒸馏/mode-b/

【执行】
python .agents/skills/story-engine/tools/verify_chapter.py --batch-all <源文目录> -o <输出目录>

生成内容（每章一个 de-ai_guide_N.md）：
- 字数/段落/句数
- 句长分布（短/中/长精确计数）
- 段落节奏（短/中/长段计数）
- 对话密度
- 句首多样性
- 连接词密度/TTR

写章agent参考这些数字对齐节奏，不是追数字。

【回传】
✅ de-ai batch | {源书名} | N章 | 输出目录:{输出目录}
