# 方寸 | AI 网文仿写引擎

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)
![GitHub Stars](https://img.shields.io/github/stars/WindXRan/fangcun-write.svg)
![GitHub Forks](https://img.shields.io/github/forks/WindXRan/fangcun-write.svg)
![GitHub Issues](https://img.shields.io/github/issues/WindXRan/fangcun-write.svg)

**从源文输入到全书量产，0 人工的 AI 小说生产线**

[快速开始](#快速开始) • [功能特性](#功能特性) • [架构设计](#架构设计) • [使用示例](#使用示例) • [贡献指南](CONTRIBUTING.md)

</div>

## 🎯 项目简介

**方寸** 是一个 AI 驱动的网文仿写引擎，专注于**全书量产**而非单章生成。

**核心价值：** 不是"帮你写一章"，而是"帮你开渔场"。

### 📸 项目截图

<!-- 在此处添加项目截图或 GIF -->
<!-- ![项目架构](docs/screenshots/architecture.png) -->
<!-- ![演示 GIF](docs/screenshots/demo.gif) -->

> 💡 **提示：** 截图和 GIF 能显著提高项目的吸引力。请参考 [截图指南](docs/screenshots.md) 添加项目截图。

### 为什么选择方寸？

| 痛点 | 方寸解决方案 |
|------|-------------|
| AI 只能写一章，写不了一本 | 六阶段流水线，覆盖从源文到全书的完整流程 |
| 质量不稳定，角色漂移 | 行为模式卡片 + 双层文笔指纹 + 七维审改系统 |
| 人工干预多，效率低 | 全自动 pipeline，30 章并行写入，0 人工 |
| 容易抄源文，换皮不彻底 | 冲突类型强制换 + 台词 0 重合 + 换皮检验 |

## ✨ 功能特性

### 🚀 六阶段流水线
```
源文输入 → 概念生成 → 章纲映射 → 并行写章 → 自动审改 → 全书输出
```

### 🧠 智能分析系统
- **行为模式卡片**：提取角色的应激/决策/情感/弱点模式
- **双层文笔指纹**：算法锚点（0 token）+ LLM 分析（精准模仿）
- **全局节奏图**：自动识别源文的节奏模式

### 🔄 双执行模式
- **API 模式**：Python 脚本直接调用 DeepSeek API，适合批量生产
- **Agent 模式**：opencode agent 派生子 agent，适合高质量单章

### 🛡️ 七维质量检查
| 检查项 | 说明 | 自动修复 |
|--------|------|----------|
| 字数偏差 | ±15% 区间控制 | ❌ |
| 比喻过多 | 源文+3 阈值 | ❌ |
| AI 路标词 | 源文+1 阈值 | ✅ |
| 直抒情过多 | 源文+2 阈值 | ❌ |
| 台词雷同 | 8 字匹配检测 | ❌ |
| AI 痕迹词 | 句首检测 | ✅ |
| LLM 审稿 | 钩子/情绪/人设 | ❌ |

### 📊 零成本对比报告
- 本地算法对比，0 token 消耗
- 自动存档，支持历史版本对比

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────┐
│  Phase 6：统一审改层                                      │
│  批次审查(7维全检) + 全局维度审查(人设/节奏/伏笔)          │
│  → 总结 → P0/P1/P2 → N个修复Agent并行修复                │
├─────────────────────────────────────────────────────────┤
│  Phase 4：对比层                                         │
│  本地算法对比（0 token），自动存档                         │
├─────────────────────────────────────────────────────────┤
│  Phase 3.5：精简层                                       │
│  超字数20%的章自动裁剪                                    │
├─────────────────────────────────────────────────────────┤
│  Phase 3：写章层                                         │
│  并行写章，超30%偏差自动重试                               │
├─────────────────────────────────────────────────────────┤
│  Phase 2：章纲层                                         │
│  节拍映射 + 冲突替换 + 高光标注                            │
├─────────────────────────────────────────────────────────┤
│  Phase 1-1.5：开书层                                     │
│  概念设定 + 文笔指纹（双层：算法锚点 + LLM分析）            │
└─────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone https://github.com/WindXRan/fangcun-write.git
cd fangcun-write

# 配置 API key
$env:API_KEY="sk-xxx"
```

### 2. 配置文件
创建 `configs/your_book.json`：
```json
{
  "book_name": "新书名",
  "author": "源文作者",
  "source_book": "源文书名",
  "rewrites_dir": "projects/作者/源书/rewrites/新书",
  "model": "deepseek-v4-pro",
  "api_key": null,
  "execution_mode": "api"
}
```

### 3. 运行命令
```bash
# 完整跑一本书（--end 指定源文总章数，--workers 控制并发）
python .agents/skills/story-engine/tools/pipeline.py \
  --config configs/your_book.json \
  --start 1 --end 100 --workers 30

# 分步执行
python .agents/skills/story-engine/tools/pipeline.py --config configs/your_book.json --phase open-book
python .agents/skills/story-engine/tools/pipeline.py --config configs/your_book.json --phase write --start 1 --end 10

# 只看 prompt 不调 API（debug 模式）
python .agents/skills/story-engine/tools/pipeline.py --config configs/your_book.json --phase write --debug

# 统一审改
python .agents/skills/story-engine/tools/unified_fixer.py --config configs/your_book.json

# Agent 模式写章
python tools/rewrite_chapters.py --config configs/your_book.json --phase write --execution-mode agent
```

## 📁 项目结构

```
projects/{作者}/{书名}/
├── _cache/chapters/第N章.txt      # 源文拆章
└── rewrites/{新书名}/
    ├── concept.md                  # 开书产物（设定+角色+行为模式+节奏图+弧线）
    ├── guides/plot_{N}.md         # 章纲（节拍映射+冲突替换+高光）
    ├── chapters/ch_{N}.txt        # 正文
    ├── styles/style_{N}.json      # 文笔指纹（双层）
    ├── compare/                    # 对比报告（本地算法，0 token）
    └── _debug/                     # --debug 模式下 prompt 存档
```

## 🎯 使用示例

### 示例 1：仿写一本美食文
```bash
# 1. 准备源文（假设是《临水小厨娘》）
# 2. 创建配置文件
# 3. 运行 pipeline
python .agents/skills/story-engine/tools/pipeline.py \
  --config configs/food_novel.json \
  --start 1 --end 50 --workers 20
```

### 示例 2：高质量单章优化
```bash
# 使用 Agent 模式写第 5 章
python tools/rewrite_chapters.py \
  --config configs/your_book.json \
  --phase write --start 5 --end 5 \
  --execution-mode agent
```

### 示例 3：质量检查与修复
```bash
# 先 dry-run 查看问题
python .agents/skills/story-engine/tools/unified_fixer.py \
  --config configs/your_book.json --dry-run

# 确认后执行修复
python .agents/skills/story-engine/tools/unified_fixer.py \
  --config configs/your_book.json
```

## 🔧 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `book_name` | 新书名称 | 必填 |
| `author` | 源文作者 | 必填 |
| `source_book` | 源文书名 | 必填 |
| `model` | 使用的模型 | `deepseek-v4-pro` |
| `reasoning_effort` | 推理强度 | `low` |
| `execution_mode` | 执行模式 | `api` |
| `api_key` | API 密钥 | 从环境变量读取 |

## 📊 性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 单章生成时间 | 30-60 秒 | 包含章纲+写章+审改 |
| 字数达标率 | 60-70% | ±10% 区间内 |
| 角色漂移率 | ~5% | 使用行为模式卡片后 |
| 并行写章数 | 30 章 | 默认 workers 设置 |
| 总流程耗时 | 2-3 小时 | 100 章完整流程 |

## 🤝 贡献指南

我们欢迎各种形式的贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

### 如何贡献？
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 报告问题
- 使用 [Bug 报告模板](https://github.com/WindXRan/fangcun-write/issues/new?template=bug_report.md)
- 使用 [功能请求模板](https://github.com/WindXRan/fangcun-write/issues/new?template=feature_request.md)

## 📈 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本更新历史。

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

<div align="center">

**如果这个项目对您有帮助，请给我们一个 ⭐️ Star！**

[![GitHub Stars](https://img.shields.io/github/stars/WindXRan/fangcun-write.svg?style=social)](https://github.com/WindXRan/fangcun-write/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/WindXRan/fangcun-write.svg?style=social)](https://github.com/WindXRan/fangcun-write/network/members)

</div>