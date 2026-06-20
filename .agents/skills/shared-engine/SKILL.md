---
name: shared-engine
description: |
  公共引擎层，为所有写作skill提供共享能力。
  其他skill通过 sys.path.insert 或 import 方式使用本skill的工具。
  安装方式：直接放入 .agents/skills/ 目录即可。
---

# shared-engine：公共引擎层

## 定位

为 story-engine、drama-engine、续写引擎、仿写引擎等提供共享能力。

## 共享能力

### 1. LLM调用 (`tools/llm/`)
- `api_client.py` - API客户端（支持多provider：deepseek/mimo/openai）
- `prompt_loader.py` - prompt加载器（变量替换、文件嵌入）
- `prompt_meta.py` - prompt元数据（frontmatter解析）

### 2. 文本分析 (`tools/analysis/`)
- `text_metrics.py` - 文本指标（字数、句长、代词密度等）
- `style_extract.py` - 风格提取（文笔指纹）
- `source_analysis.py` - 事件提取/故事骨架/改编策略

### 3. 文件IO (`tools/io/`)
- `source_io.py` - 源文读写（events/skeleton/adaptation）
- `state_manager.py` - 状态管理（断点续传）
- `file_utils.py` - 通用文件工具

### 4. 工具函数 (`tools/utils/`)
- `progress.py` - 进度条
- `retry.py` - 重试机制
- `cache.py` - 缓存管理

## 使用方式

其他skill在使用时：

```python
# 方式1：sys.path.insert（推荐）
import sys
from pathlib import Path
shared_tools = Path(__file__).parent.parent.parent / "shared-engine" / "tools"
sys.path.insert(0, str(shared_tools))

# 方式2：直接import（需要shared-engine在PYTHONPATH中）
from llm.api_client import call_llm
from analysis.text_metrics import count_metrics
from io.source_io import load_events
```

## 依赖关系

```
shared-engine (基础层)
    ↑
    ├── story-engine (长篇仿写)
    ├── drama-engine (短剧改编)
    ├── story-continue (小说续写) [未来]
    ├── drama-continue (剧本续写) [未来]
    └── story-imitate (仿写引擎) [未来]
```

## 安装

```bash
# 直接复制到skills目录即可
cp -r shared-engine .agents/skills/
```

## 配置

shared-engine 不需要独立配置，使用各engine的config即可。
