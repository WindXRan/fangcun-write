---
name: story-cover
description: |
  小说封面生成。根据书名自动分析题材风格，生成封面prompt或调用 GPT-Image-2 直接生成封面。
  触发方式：/story-cover、/封面、「帮我做个封面」「生成封面图」
  注意：封面只显示书名，不显示作者名。
---

# story-cover · 小说封面生成

## 功能

根据书名、题材风格，生成封面prompt。默认只输出prompt，用户可自行去DALL-E/Midjourney/可灵等平台生成封面。

## 使用方式

```
/story-cover
```

用户提供：
- 书名
- 题材风格（可选，会自动分析）
- OpenAI API Key（可选，提供则直接生成封面）

## 流程

1. 分析书名，判断题材风格（古言/现言/玄幻/都市等）
2. 生成封面 prompt（**只含标题文字**，不含作者名）
3. **默认**：输出prompt，用户自行生成
4. **有key**：调用 `gpt-image-2` 模型生成封面，输出 PNG 文件

## 输出格式

### 默认（无key）

```
## 封面Prompt

（可直接复制到 DALL-E / Midjourney / 可灵 使用）

prompt: ...
```

### 有key

```
正在生成封面...
封面已保存：{书名}_封面.png
```

## API调用示例（用户提供key时）

```python
from openai import OpenAI
import base64

client = OpenAI(api_key="your_openai_api_key")

response = client.images.generate(
    model="gpt-image-2",
    prompt="封面prompt...",
    size="1024x1536",  # 竖版封面
    quality="high",
    n=1
)

image_data = base64.b64decode(response.data[0].b64_json)
with open("cover.png", "wb") as f:
    f.write(image_data)
```

## 注意事项

- 默认只输出prompt，不调用API
- 用户提供OpenAI key时才生成封面
- 必须使用 `gpt-image-2` 模型
- 尺寸建议：`1024x1536`（竖版）或 `1536x1024`（横版）
- 不支持DeepSeek，只支持OpenAI

## 输出

封面文件保存到项目根目录：`{书名}_封面.png`