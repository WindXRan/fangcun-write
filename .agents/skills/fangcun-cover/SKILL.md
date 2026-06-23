---
name: fangcun-cover
version: 1.0.0
description: |
  小说封面生成。根据书名、作者名自动分析题材风格，调用 GPT-Image-2 生成封面。
  触发方式：/fangcun-cover、/封面、「帮我做个封面」「生成封面图」
---

# fangcun-cover：小说封面生成

你是小说封面设计师。根据书名和题材，调用 GPT-Image-2 一次性生成包含书名和作者名的完整封面。

**核心原则：封面是读者的第一印象，一眼传达题材和氛围。**

---

## 环境变量

| 变量 | 必填 | 默认 | 说明 |
|:-----|:----:|:-----|:-----|
| `GPT_IMAGE_API_KEY` | ✅ | — | OpenAI 或兼容代理的 API Key |
| `GPT_IMAGE_BASE_URL` | | `https://api.openai.com/v1` | 兼容代理时改这个 |
| `GPT_IMAGE_MODEL` | | `gpt-image-2` | 仅在测试新模型时覆盖 |
| `GPT_IMAGE_SIZE` | | `1024x1536` | 竖版封面比例 |

---

## 生成流程

### Step 1：收集信息

必填：书名、作者名（笔名）、目标平台
选填：参考图、风格偏好、尺寸

### Step 2：题材判定

扫描书名中的关键词，选定题材：
- 单题材命中 → 直接采用
- 多题材命中 → 按优先级：仙侠 > 西幻 > 古言 > 现言 > 都市 > 悬疑 > 科幻 > 历史 > 灵异 > 轻小说
- 零命中 → 默认 `都市`

### Step 3：构建提示词

提示词 = **文字层** + **风格层** + **画面层**，全部用英文编写。

#### 书名字体风格

| 题材 | 描述关键词 |
|:-----|:-----------|
| 玄幻/仙侠 | `bold golden brush calligraphy with metallic glow` |
| 都市 | `modern bold sans-serif with metallic silver finish` |
| 古言/宫斗 | `elegant golden traditional Kai script` |
| 现言/甜宠 | `soft rounded handwritten style in white with pink glow` |
| 悬疑/推理 | `distorted bold cracked letters in blood red` |
| 科幻/末世 | `neon glowing futuristic font in electric blue` |
| 西幻 | `metallic embossed fantasy lettering with glow effect` |
| 历史/军事 | `heavy stone-carved seal script in deep red` |
| 灵异/恐怖 | `eerie dripping handwritten font in sickly green` |
| 轻小说 | `colorful cartoon outlined bubbly font` |

#### 完整提示词模板

```
Chinese web novel cover design, [平台风格].
Title text '{书名}' at top center in [书名字体风格].
Author name '{作者名}' at bottom center in [作者名字体风格].
[题材风格标签]. [人物描述]. [背景描述].
[色彩指令]. [光效指令].
Professional book cover, high detail digital painting, portrait 2:3 ratio, no watermark
```

### Step 4：调用 API 并保存

```bash
curl -fsS --max-time 180 \
  "$BASE_URL/images/generations" \
  -H "Authorization: Bearer $GPT_IMAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"prompt\":\"$PROMPT\",\"size\":\"$SIZE\"}"
```

### Step 5：质量检查

| 检查项 | 标准 |
|:-------|:-----|
| 文字渲染 | 书名清晰可辨，字体风格匹配题材 |
| 题材匹配 | 视觉风格与书名题材一致 |
| 构图合理 | 主体突出，文字不遮挡核心画面 |
| 平台适配 | 符合目标平台的封面风格调性 |
