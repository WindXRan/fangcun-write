# 方寸

网文仿写引擎。读一本源文 → 自动生成换皮新书。

**核心思路**：不修单章，只修 pipeline。防线在流程里——算法锚点 + LLM 指纹 + 多 Agent 审改，0 人工。

## 快速开始

```bash
# 1. 配置 API key
$env:API_KEY="sk-xxx"

# 2. 完整跑一本书
python .agents/skills/story-engine/tools/pipeline.py \
  --config configs/xxx.json \
  --start 1 --end 188 --workers 30

# 3. 分步执行
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase open-book
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase write --start 1 --end 10

# 4. 只看 prompt 不调 API（debug 模式）
python .agents/skills/story-engine/tools/pipeline.py --config configs/xxx.json --phase write --debug
```

## Pipeline

```
Phase 1:  开书       → concept.md  （设定+角色+节奏图+弧线）
Phase 1.5: 文笔指纹   → style_N.json （10项算法锚点 + LLM正反面分析）
Phase 2:  章纲       → plot_N.md   （节拍映射+冲突替换+高光）
Phase 3:  写章       → ch_N.txt    （并行，超30%偏差自动重试）
Phase 3.5: 精简      → 超字数20%的章自动裁剪
Phase 4:  对比       → compare/报告（本地算法，0 token）
Phase 6:  审改       → 混合架构：批次审查 + 全局维度审查 → 汇总 → 修复
```

## 文笔指纹（双层）

写章时每个源文章节生成双层指纹，注入 prompt：

- **Layer 1 — 算法锚点（0 token）**：句长/对话比/段长/代词密度/词汇丰富度/标点风格/开头结尾类型，纯正则 <30ms
- **Layer 2 — LLM 分析（1 次 flash 调用）**：提取 2-3 个可复制写法特征+原文例句，2 个易被 AI 写走样的点

## 统一审改（Phase 6）

```
Layer 1a: N 个 Agent 各审 10 章（7 维全检）
Layer 1b: 2 个 Agent 通读全书 —— 人设一致性 / 全局节奏伏笔
    ↓
总结 Agent → 去重 → P0/P1/P2
    ↓
N 个修复 Agent 并行修复
```

## 目录结构

```
projects/{作者}/{书名}/
├── _cache/chapters/第N章.txt      # 源文拆章
└── rewrites/{新书名}/
    ├── concept.md                  # 开书产物
    ├── guides/plot_{N}.md         # 章纲
    ├── chapters/ch_{N}.txt        # 正文
    ├── styles/style_{N}.json      # 文笔指纹
    ├── compare/                    # 对比报告
    └── _debug/                     # --debug 模式下 prompt 存档
```

## config.json

```json
{
  "book_name": "新书名",
  "author": "源文作者",
  "source_book": "源文书名",
  "rewrites_dir": "projects/作者/源书/rewrites/新书",
  "model": "deepseek-v4-flash",
  "api_key": null
}
```

`api_key` 为 null 时从 `$env:API_KEY` 读取。

## 模型策略

| 阶段 | 模型 |
|------|------|
| 开书 | pro, reasoning=high |
| 章纲/写章/指纹/审改 | flash |

## License

MIT
