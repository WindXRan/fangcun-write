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
- **write** - 写章（注入角色卡+大纲+前文）
- **trim** - 精简（保留剧情，删冗余）
- **polish** - 润色（改文笔，不改内容）
- **expand** - 扩写（增加细节）
- **rewrite** - 重写（整章重写）

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

## 使用方式

### 方式1：作为独立 skill 使用

```bash
# 写章
python tools/pipeline.py --config config.json --phase write --start 1 --end 10

# 精简
python tools/pipeline.py --config config.json --phase trim --start 1 --end 10

# 润色
python tools/pipeline.py --config config.json --phase polish --start 1 --end 10

# 扩写
python tools/pipeline.py --config config.json --phase expand --start 1 --end 10

# 重写
python tools/pipeline.py --config config.json --phase rewrite --start 1 --end 10
```

### 方式2：作为库被其他引擎调用

```python
# 在其他引擎中
import sys
from pathlib import Path
writer_tools = Path(__file__).parent.parent.parent / "writer-engine" / "tools"
sys.path.insert(0, str(writer_tools))

from writer import write_chapter
from trim import trim_chapter
from polish import polish_chapter
from expand import expand_chapter
from rewrite import rewrite_chapter
```

## 输入/输出

### 输入
- `config.json` - 配置文件（API配置、目录路径）
- `chapters/` - 已有章节（trim/polish/expand/rewrite 时需要）
- `guides/` - 章纲（write 时需要）
- `analysis/` - 分析结果（角色卡、关系线等）

### 输出
- `chapters/ch_N.txt` - 生成/修改的章节

## 质量检查

每个操作后自动检查：
- 字数是否在目标范围内
- 角色名是否一致
- 是否有AI痕迹
