---
name: fangcun-continue
description: |
  小说续写/第二部引擎。基于已有小说，AI自主设计续写方案，用户确认后执行。
  触发方式：「续写」「写第二部」「继续写」「出第二部」
---

# fangcun-continue：小说续写引擎

## 定位

基于已有小说，AI自主设计续写方案，用户确认后执行。

## 与仿写引擎的区别

| 仿写引擎 | 续写引擎 |
|---------|---------|
| 换皮不换骨 | 保留人设，新故事 |
| 有源文参照 | 自由创作 |
| 对标源文节奏 | 新节奏设计 |
| 角色名必须换 | 角色名保留 |

## 流程

```
分析 → 方案设计 → 用户确认 → 大纲生成 → 逐章写作 → 质量审核
```

## 使用方式

```bash
# 分析已有小说
python tools/pipeline.py --config config.json --phase analyze

# 生成续写方案（AI自主设计）
python tools/pipeline.py --config config.json --phase plan

# 用户确认方案后，生成大纲
python tools/pipeline.py --config config.json --phase outline

# 逐章写作
python tools/pipeline.py --config config.json --phase write --start 1 --end 20

# 质量审核
python tools/pipeline.py --config config.json --phase review
```

## 配置文件

```json
{
  "source_book": "认亲后，画风跑偏",
  "source_author": "午夜凶球",
  "continue_name": "认亲后2：画风更偏了",
  "time_jump": "5年后",
  "api_key": null,
  "model": "mimo-v2.5-pro",
  "base_dir": ".",
  "rewrites_dir": "projects/午夜凶球/认亲后，画风跑偏/rewrites/认亲后2"
}
```

## 输出结构

```
projects/{作者}/{源书名}/rewrites/{续写书名}/
├── analysis/           # 第一部分析
│   ├── characters.md   # 角色库
│   ├── world.md        # 世界观
│   ├── relationships.md # 关系线
│   └── ending_state.md # 结局状态
├── plans/              # 续写方案
│   ├── plan_a.md       # 方案A
│   ├── plan_b.md       # 方案B
│   └── plan_c.md       # 方案C
├── outline/            # 大纲
│   └── outline.md      # 确认后的大纲
├── chapters/           # 章节
│   ├── ch_001.txt
│   └── ...
└── export/             # 导出
    └── {续写书名}.txt
```

## AI自主设计能力

### 方案设计
- 基于原有人设的合理延伸
- 时间跳跃点选择
- 新冲突设计
- 情感线发展

### 大纲生成
- 基于用户选择的方案
- 保持角色一致性
- 创造新的故事弧线

### 逐章写作
- 注入：原角色卡 + 前3章摘要 + 大纲
- 质量检查（一致性/风格）
- 更新状态

## 质量检查

- 角色一致性检查
- 情节连贯性检查
- 风格偏离检查
- 伏笔回收检查
