---
name: writer-engine
description: |
  通用写作能力引擎。提供 write/trim/polish/expand/rewrite 五大写作能力。
  其他 skill（story-engine、story-continue、drama-engine）通过 import 方式调用。
  触发方式：/writer-engine、/写章、/精简、/润色、/扩写、/重写
---

# writer-engine：通用写作能力引擎

## 定位

提供五大写作能力，供其他引擎调用：
- **write** - 写章（注入角色卡+大纲+前文+文笔指纹+风格约束）
- **trim** - 精简（字数锚点控制，保留剧情）
- **polish** - 润色（对比源文风格，去AI味）
- **expand** - 扩写（增加细节）
- **rewrite** - 重写（文笔指纹+角色卡+多样性自检）

## 与其他引擎的关系

```
shared-engine (底层：API/IO/分析)
       ↑
writer-engine (写作能力)
       ↑
       ├── story-engine (长篇仿写)
       ├── story-continue (续写)
       ├── drama-engine (短剧改编)
       └── drama-continue (剧本续写)
```

## 双模式

| 模式 | 用途 | 源文对比 | prompt来源 |
|------|------|----------|-----------|
| `imitation`（默认） | 仿写 | ✅ 有 | 根目录 prompt（story-engine 同源 v22） |
| `continue` | 续写 | ❌ 无 | continue/ 目录 prompt |

## 使用方式

### 方式1：作为独立 skill 使用

```bash
# 仿写模式（默认）
python tools/pipeline.py --config config.json --phase write --start 1 --end 10

# 续写模式
python tools/pipeline.py --config config.json --phase write --start 1 --end 10 --mode continue

# 并发写章
python tools/pipeline.py --config config.json --phase write --start 1 --end 10 --workers 5

# 精简/润色/扩写
python tools/pipeline.py --config config.json --phase trim --start 1 --end 10
python tools/pipeline.py --config config.json --phase polish --start 1 --end 10
python tools/pipeline.py --config config.json --phase expand --start 1 --end 10

# 重写
python tools/pipeline.py --config config.json --phase rewrite --start 1 --end 10 --reason "人设崩塌"
```

### 方式2：作为库被其他引擎调用

```python
import sys
from pathlib import Path
writer_tools = Path(__file__).parent.parent.parent / "writer-engine" / "tools"
sys.path.insert(0, str(writer_tools))

from writer import write_chapter, trim_chapter, polish_chapter, expand_chapter, rewrite_chapter

# 写章（仿写模式）
result = write_chapter(config, ch_num, mode="imitation")

# 写章（续写模式）
result = write_chapter(config, ch_num, mode="continue")

# 精简/润色/扩写
result = trim_chapter(config, ch_num, mode="imitation")
result = polish_chapter(config, ch_num, mode="imitation")
result = expand_chapter(config, ch_num, mode="imitation")

# 重写
result = rewrite_chapter(config, ch_num, mode="imitation", reason="字数不足")
```

## config.json 配置

```json
{
  "book_name": "新书名",
  "rewrites_dir": "projects/作者/源书/rewrites/新书",
  "source_dir": "projects/作者/源书",
  "author_name": "作者名",
  "source_book_name": "源书名",
  "source_chars": 2500,
  "source_sent_len": 15,
  "source_dialog_ratio": 40,
  "source_para_len": 60,
  "writing_fingerprint": "文笔指纹（正面指令+反面踩雷）",
  "style_type": "喜剧/轻喜剧/温馨日常/甜宠",
  "scene_mechanism": "误会→反转→升级→吐槽",
  "info_release": "第1章只暗示两家关系好",
  "character_cards": "角色行为卡片",
  "female_lead": "女主名",
  "male_lead": "男主名",
  "worldview": "世界观设定"
}
```

## 输入/输出

### 输入
- `config.json` - 配置文件（API配置、目录路径、源文分析数据）
- `chapters/` - 已有章节（trim/polish/expand/rewrite 时需要）
- `guides/` - 章纲（write 时需要）
- `analysis/` - 分析结果（角色卡、关系线等）

### 输出
- `chapters/ch_N.txt` - 生成/修改的章节

## 质量检查

每个操作后自动检查：
- 字数是否在目标范围内
- AI路标词是否超标（对比源文）
- 代词密度是否偏离源文
- 句长节奏是否偏离源文
