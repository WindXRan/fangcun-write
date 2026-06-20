---
name: fangcun-analyze
description: |
  源书级分析引擎。提取事件表、生成故事骨架、制定改编策略。产物供 fangcun-novel 和 fangcun-drama 共用。
  触发方式：「提取事件」「生成骨架」「分析这本书」「源书分析」
allowed-tools: Bash(python *)
---

# fangcun-analyze：源书级分析引擎

## 你是 agent，负责：

1. **理解用户意图**（"分析这本书" → 跑全流程；"重新提取事件" → 只跑 event）
2. **组装正确的命令**
3. **检查输出质量**
4. **处理错误**

## 产物（存放在 _cache/，两套引擎共用）

| 文件 | 说明 |
|------|------|
| `events.json` | 事件表（每章一行：角色/事件/主线关系/情绪） |
| `story_skeleton.md` | 故事骨架（三幕/分集/付费卡点/反转） |
| `adaptation_strategy.md` | 改编策略（8大要点/删减决策/世界观） |
| `styles/style_{N}.md` | 文笔指纹（算法锚点 + LLM 风格分析） |

## 流程

```bash
# 全流程（事件→骨架→改编）
python .agents/skills/fangcun-analyze/tools/pipeline.py --config {config} --phase all

# 分步执行
python .agents/skills/fangcun-analyze/tools/pipeline.py --config {config} --phase event       # 事件提取
python .agents/skills/fangcun-analyze/tools/pipeline.py --config {config} --phase skeleton     # 故事骨架
python .agents/skills/fangcun-analyze/tools/pipeline.py --config {config} --phase adaptation   # 改编策略
python .agents/skills/fangcun-analyze/tools/pipeline.py --config {config} --phase review       # 质量审核

# 查看状态
python .agents/skills/fangcun-analyze/tools/pipeline.py --config {config} --phase status
```

## 配置文件

```json
{
  "base_dir": ".",
  "author": "作者名",
  "source_book": "源书名",
  "api_key": "sk-xxx",
  "api_base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat"
}
```

### 使用 FreeLLMAPI（免费额度聚合）

部署 FreeLLMAPI 后，配置改为：

```json
{
  "api_key": "freellmapi-xxx",
  "api_base_url": "http://localhost:3001/v1",
  "model": "auto"
}
```

FreeLLMAPI 自动选择最佳可用模型，一个 provider 限流时自动切换到下一个。详见 [FreeLLMAPI 文档](https://github.com/tashfeenahmed/freellmapi)。

## 质量检查（agent 自动执行）

跑完后 agent 应该：
1. 读 `events.json`，检查有效事件数是否等于总章数
2. 读 `story_skeleton.md`，检查分集数是否合理
3. 读 `reviews/` 目录，汇报审核评分
4. 如有失败章节，建议重跑

## 常见场景

| 用户说 | agent 做 |
|--------|----------|
| "分析这本书" | 跑全流程 --phase all |
| "重新提取事件" | 跑 --phase event（增量，已有跳过） |
| "骨架有问题" | 跑 --phase skeleton（覆盖旧的） |
| "看看分析结果" | 读 events.json + story_skeleton.md，汇报 |
