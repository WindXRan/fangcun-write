---
version: 5
changelog: 指令前置+精简去重
type: user
phase: guides
description: 章纲生成
required_vars: ["N", "新书名", "作者名", "源书名", "源文全文", "目标字数", "目标字数_min", "目标字数_max", "源文字数"]
optional_vars: ["genre"]
system_prompt: system-generic.md
defaults: {"model": "deepseek-v4-flash", "max_tokens": 8192, "reasoning_effort": "low", "temperature": 0.8}
---
为《{新书名}》第{N}章生成写章指南（章纲）。

换皮：成品剥掉人名地名后认不出源文。对标升级不换赛道，每章至少一个源文没有的亮点。

节拍表：只写结构功能+冲突类型+情绪目标+强度，禁止具体动作/场景/道具/台词/人名。正确："引入同级实力者形成对比"错误："风灵儿测试展示八段灵力"。节拍要素：结构功能/冲突类型(身份/利益/信息差/道德)/情绪目标(紧张/心疼/甜/燃)/强度(低中高爆)

**约束：人名与characters.md一致。源文时间压力/冲突触发/关键道具/动作链/情绪链/数字编号全部换掉。本章自洽与前章连贯，不要求与源文一致。**

任务：读settings→抽象拆源文(只取情绪功能)→对标升级→按情绪占比分配字数→节拍表只填抽象指引

数据：源文{源文字数}字 | 新书{目标字数}字({目标字数_min}-{目标字数_max})

输出格式(不带#/---，行首冒号)：
章名：2-6字 | 释放信息：源文释放/未释放
节拍表：|#|结构功能|冲突类型|情绪|强度|功能定位|字数|
高光：位置|类型|一句话
鼓点：|段|字数|情绪|感官|
排除项：无违规

【参考设定】projects/{作者名}/{源书名}/rewrites/{新书名}/settings/characters.md
【参考剧情】projects/{作者名}/{源书名}/rewrites/{新书名}/settings/plot.md
【参考世界观】projects/{作者名}/{源书名}/rewrites/{新书名}/settings/world.md

{源文全文}
