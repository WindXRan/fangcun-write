---
name: story-genre
description: 网文品类自动检测。读源文首章+header，LLM 判定品类（都市擦边/修仙升级/古言甜宠等），自动归一化别名并注册新品类。触发词：检测品类、品类判定、genre检测
---

# 网文品类检测

LLM 驱动，Zero-shot 品类判定，无需预训练。

## 适用场景

- 开书前不知道源文是什么品类
- 品类为空时自动检测（Phase 0）
- 新品类自动注册到 `genre_aliases.json`（脚本自动完成）

## 用法

```bash
# CLI 直接调用
python tools/detect_genre.py configs/xxx.json

# 作为模块导入
from tools.detect_genre import detect_genre
genre = detect_genre(config)
```

## 品类体系

| 品类 | 特征 |
|------|------|
| 都市擦边 | 男频，都市，系统/后宫，擦边浓度高 |
| 修仙升级 | 玄幻/修仙，修炼升级打怪 |
| 都市系统 | 男频，都市，系统文，擦边低 |
| 古言甜宠 | 女频，古代，感情线 |
| 现言甜宠 | 女频，现代，感情线 |
| 脑洞无敌流 | 脑洞+无敌+搞笑 |
| 悬疑惊悚 | 悬疑推理/恐怖惊悚 |
| 异能觉醒 | 超能力/觉醒 |
| 末日废土 | 末世生存/废土 |

未匹配时 LLM 自动创建新品类，写入 `genre_aliases.json`。

## 文件

```
.agents/skills/story-genre/
├── SKILL.md
└── tools/
    ├── detect_genre.py      # 品类检测主逻辑
    └── genre_aliases.json   # 别名归一化映射（自动维护）
```
