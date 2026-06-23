---
name: open-book
description: |
  开书task。创建新书的标准流程。
  触发方式：「开书」「创建新书」「开始写新书」
---

# open-book：开书引擎

## 触发条件

当用户说以下内容时，加载本skill：
- 「开书」
- 「创建新书」
- 「开始写新书」

## 加载方式

读取并加载 system prompt：`.prompts/system/open-book.md`

## 你是 agent，负责：

1. **理解用户意图**（"开书" → 跑全流程；"只创建大纲" → 只跑 outline）
2. **组装正确的命令**
3. **检查输出质量**
4. **处理错误**

## 产物

| 文件 | 说明 |
|------|------|
| `outline.md` | 大纲（核心主题/主要角色/主线剧情/核心冲突/写作要求） |
| `characters.md` | 角色设定（5-10个角色，详细信息） |
| `world.md` | 世界观设定（地点/时间线/社会背景/核心主题） |
| `chapter_outline.md` | 章纲（每章详细规划） |

## 流程

### Phase 1: 确认开书信息

确认以下信息：
- 书名
- 作者
- 类型（长篇/短篇）
- 主题
- 参考作品（可选）

### Phase 2: 创建大纲

```bash
python .agents/skills/open-book/tools/pipeline.py --config {config} --phase outline
```

- 核心主题
- 主要角色
- 主线剧情（分卷/分章）
- 核心冲突
- 写作要求

### Phase 3: 创建角色设定

agent 自己执行：
1. 读取 `outline.md`
2. 生成角色设定
3. 写入 `characters.md`

### Phase 4: 创建世界观设定

agent 自己执行：
1. 读取 `outline.md`
2. 生成世界观设定
3. 写入 `world.md`

### Phase 5: 创建章纲

agent 自己执行：
1. 读取 `outline.md`
2. 读取 `characters.md`
3. 生成章纲
4. 写入 `chapter_outline.md`

## 配置文件

```json
{
  "book_name": "书名",
  "author": "作者名",
  "type": "长篇/短篇",
  "theme": "主题",
  "reference": "参考作品，可选",
  "output_dir": "projects/{作者}/{书名}"
}
```

## 质量检查

跑完后 agent 应该：
1. 检查所有文件是否生成
2. 检查大纲是否完整（核心主题、主要角色、主线剧情、核心冲突、写作要求）
3. 检查角色设定是否完整（5-10个角色，每个角色有详细信息）
4. 检查世界观设定是否完整（地点、时间线、社会背景、核心主题）
5. 检查章纲是否完整（每章的详细规划）

## 常见场景

| 用户说 | agent 做 |
|--------|----------|
| "开书" | 跑全流程（outline → characters → world → chapter_outline） |
| "只创建大纲" | 跑 --phase outline |
| "角色设定有问题" | 重新跑 characters（agent 模式） |
| "看看开书结果" | 读所有文件，汇报 |