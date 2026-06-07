---
name: story-engine
description: |
    仿写引擎 guide模式：开书→生成guide→写章→批后。
    每章2个guide（plot+style），写章agent只管拿着guide写。
    触发条件：用户说「仿写」「用vPlan写」「帮我仿写这本书」「写第N章」「继续写」。
    不要在用户只是问「怎么写小说」「帮我写大纲」时触发。
allowed-tools: Bash(python *) Bash(cat *) Bash(ls *) Bash(cp *) Bash(mkdir *)
shell: powershell
---

# story-engine（guide模式）

> 开书→生成guide→写章→批后。分析与创作分离，guide驱动写作。

## 文件结构

```
novel-download-authors/{作者名}/{源书名}/仿写/{新书名}_仿写/
├── 设定/
│   ├── 新书设定.md
│   ├── 全书弧线.md
│   └── guides/
│       ├── plot_guide_N.md
│       └── style_guide_N.md
├── 追踪/
│   └── 真相.md
└── 正文/第N章.txt
```

## 工具

| 工具 | 脚本 | 用途 |
|------|------|------|
| 拆章 | `tools/split_chapters_generic.py` | 将源文.txt拆分为章节文件 |
| 合并 | `tools/merge_chapters.py` | 将章节文件合并为完整小说 |
| 风格分析 | `tools/calc_style_profile.py` | 分析源文风格特征 |
| 项目创建 | `tools/create_templates.py` | 创建项目目录结构 |
| 对比 | `.agents/skills/story-compare/compare.py` | 生成仿写书与源文的逐章对比报告 |
| API批量生成 | `tools/api_batch_generate.py` | 直接调用LLM API批量生成章节 |
| 全书自动生成 | `tools/generate_book.py` | 一次性跑完一整本书（guide+写章+对比+合并） |

## Pipeline

```
拆章+风格分析+创建目录 → 开书(2 agents) → Guide生成(1 agent) → 写章(10 agents×N批) → 批后
```

## 开书（2 agents 串行）

| 顺序 | Agent | Prompt | 输出 |
|------|-------|--------|------|
| 1 | A1：新书设定 | `prompts/arc-concept.md` | `设定/新书设定.md` |
| 2 | A2：全书弧线 | `prompts/arc-skeleton-core.md` | `设定/全书弧线.md` + `追踪/真相.md` |

## Guide 生成（1 agent，出20个文件）

1个agent读源文第1-10章 + 弧线 + 设定 + style_profile_1~10，一次性生成全部guide：
- `设定/guides/plot_guide_1.md` ~ `plot_guide_10.md`
- `设定/guides/style_guide_1.md` ~ `style_guide_10.md`

### Guide 模板

模板文件在 `templates/` 目录，prompt 在 `prompts/` 目录。
改模板只改 `templates/`，prompt 自动引用。

| 模板 | 用途 |
|------|------|
| `templates/plot_guide.md` | plot_guide 的输出结构 |
| `templates/style_guide.md` | style_guide 的输出结构 |

## 写章（10 agents × N批）

每批10章并行。每个写章 agent 只读2个文件：
1. `plot_guide_N.md`（写什么）
2. `style_guide_N.md`（怎么写）

⛔ **一次出稿。不出中间产物，不重写。**

### API批量生成（推荐）

直接调用LLM API，速度更快，真正并行：

```bash
python .agents/skills/story-engine/tools/api_batch_generate.py --config config.json --start 1 --end 10 --workers 10
```

#### DeepSeek API配置（推荐）

开书用pro，写正文用flash：

```bash
# 开书（pro模型，高质量）
python .agents/skills/story-engine/tools/api_batch_generate.py --config .agents/skills/story-engine/config_deepseek_pro.json --start 1 --end 2 --workers 2

# 写正文（flash模型，高速度）
python .agents/skills/story-engine/tools/api_batch_generate.py --config .agents/skills/story-engine/config_deepseek_flash.json --start 1 --end 10 --workers 10
```

配置文件：
- `config_deepseek_pro.json`：开书用（deepseek-v4-pro，reasoning_effort=high）
- `config_deepseek_flash.json`：写正文用（deepseek-v4-flash，reasoning_effort=low）

#### 其他API配置

```json
{
  "book_name": "染指枭雄仿写",
  "author": "初点点",
  "source_book": "染指枭雄",
  "provider": "openai",
  "model": "gpt-4",
  "api_key": "YOUR_API_KEY_HERE",
  "base_url": null,
  "system_prompt": "你是一个专业的网文写手，擅长仿写风格迁移。",
  "prompts_dir": ".agents/skills/story-engine/prompts",
  "output_dir": "仿写/染指枭雄仿写/正文"
}
```

支持的API提供商：
- `deepseek`：DeepSeek API（推荐，配置文件已准备好）
- `openai`：OpenAI API（需设置OPENAI_API_KEY）
- `anthropic`：Anthropic API（需设置ANTHROPIC_API_KEY）
- `其他`：任何OpenAI兼容API（需设置api_url）

环境变量配置：
```bash
# Windows PowerShell
$env:API_KEY="your_api_key_here"

# 或创建.env文件
API_KEY=your_api_key_here
```

### 每批写完后自动生成对比

每批10章写完后，立即运行对比生成报告：

```bash
python .agents/skills/story-compare/compare.py "<项目目录>" <起始章> <结束章>
```

示例（第1批1-10章）：
```bash
python .agents/skills/story-compare/compare.py "novel-download-authors/初点点/染指枭雄/仿写/染指枭雄仿写" 1 10
```

对比报告用于：
- 质量评估：查看仿写书与源文的风格差异
- 问题发现：检测AI痕迹、风格偏离
- 指导调整：指导下一批写章的风格变异

### 全书自动生成（一键跑完）

一次性跑完一整本书（走标准流程）：

```bash
python .agents/skills/story-engine/tools/generate_book.py --config .agents/skills/story-engine/config_full_book.json --source "novel-download-authors/闻栖/女配一睁眼，失忆男主冷脸洗床单.txt" --chapters 188
```

配置文件：`config_full_book.json`

```json
{
  "book_name": "女配一睁眼失忆男主冷脸洗床单仿写",
  "author": "闻栖",
  "source_book": "女配一睁眼，失忆男主冷脸洗床单",
  "api_key": "sk-f04fa725c7c54f3bb42d19e4cad50871",
  "system_prompt": "你是一个专业的网文写手，擅长仿写风格迁移。",
  "prompts_dir": ".agents/skills/story-engine/prompts",
  "output_dir": "novel-download-authors/闻栖/女配一睁眼，失忆男主冷脸洗床单/仿写/女配一睁眼失忆男主冷脸洗床单仿写"
}
```

**标准流程（9步）：**
1. 拆章：源文.txt → 源文章节/第N章.txt
2. 风格分析：源文 → 风格数据.json
3. 创建项目目录：设定/ + 追踪/ + 正文/
4. 开书（pro模型）：生成新书设定.md + 全书弧线.md + 真相.md
5. 生成guide（flash模型）：生成plot_guide_N.md + style_guide_N.md
6. 写章（flash模型）：读guide，按guide写正文
7. 修复章节标题：从源文提取标题，修复生成的章节文件
8. 合并导出：正文/第N章.txt → 新书.txt
9. 对比：生成对比报告

预计时间：
- 188章：约10-15分钟
- 速度：约3-5秒/章

## 批后处理

| 检查项 | 说明 |
|--------|------|
| 分层Critic | Theme→Character→Plot 三层检查 |
| 冲突检测 | 角色位置/关系阶段/伏笔状态矛盾 |
| 分布一致性 | 最近20章句长/对话比方差，过小=AI特征 |

## 导出

```bash
python .agents/skills/story-engine/tools/merge_chapters.py <项目目录>/正文/ <项目目录>/<新书名>.txt
```
