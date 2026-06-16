# story-overseas

出海引擎：把仿写好的中文小说翻译成英文，适配 Webnovel/Wattpad 等海外平台。

## 功能

1. **批量翻译** — 中文章 → 英文章，保留原文风格
2. **文化适配** — 中式表达 → 英文网文习惯
3. **平台格式** — 输出符合 Webnovel/Wattpad 格式
4. **质量校验** — 检查翻译质量、术语一致性

## 用法

```bash
# 单章翻译
python tools/overseas.py --config configs/xxx.json --chapter 1

# 批量翻译
python tools/overseas.py --config configs/xxx.json --start 1 --end 100

# 导出 Webnovel 格式
python tools/overseas.py --config configs/xxx.json --export webnovel
```

## 输出结构

```
rewrites/{新书名}/
├── chapters/          # 中文原版
├── chapters_en/       # 英文翻译版
└── export/
    ├── webnovel/      # Webnovel 格式
    └── wattpad/       # Wattpad 格式
```

## 翻译策略

- **直译+意译混合**：对话直译，叙述意译
- **文化替换**：年代文背景 → 英文读者熟悉的时代背景
- **术语表**：角色名/地名统一翻译，保持一致性
- **风格保留**：句式节奏、对话风格对标源文

## 平台要求

### Webnovel
- 每章 1500-3000 词
- 标题格式：Chapter N: Title
- 无中文标点
- 段落空行分隔

### Wattpad
- 每章 1000-2000 词
- 标题自由格式
- 支持少量格式标记
