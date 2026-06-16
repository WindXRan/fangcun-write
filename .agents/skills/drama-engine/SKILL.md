# Skill: drama-engine

# 剧本引擎 — 小说改红果短剧

一章一集，每集1分钟（约1200字）。

## 流程

```
读章节 → 改编剧本 → 导出
```

## 用法

```bash
# 完整流程
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json

# 指定范围
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --start 1 --end 10

# 只导出
python .agents/skills/drama-engine/tools/pipeline.py --config configs/drama_xxx.json --phase export
```

## 配置文件

```json
{
  "novel_name": "原著书名",
  "drama_name": "剧本名",
  "source_dir": "projects/作者/书名/_cache/chapters",
  "output_dir": "projects/作者/书名/drama",
  "api_key": null,
  "model": "deepseek-v4-pro"
}
```

## 红果短剧格式

```
第X集 标题

场景：外景/内景 - 地点 - 时间

[角色名]（动作/表情）
对白。

[画面描述]
视觉描述。
```

## 输出

- 每集：`output_dir/ep_NNN.txt`
- 合并：`output_dir/剧本名.txt`
