# Skill: story-tools

# story-tools · 通用工具包

被多个skill共享的通用工具集。

## 工具列表

| 工具 | 说明 |
|------|------|
| `split_chapters.py` | 拆章工具（番茄格式） |
| `split_chapters_generic.py` | 通用拆章工具 |
| `merge_chapters.py` | 合并章节 |
| `fix_chapter_titles.py` | 修复章节标题 |
| `create_templates.py` | 创建项目模板 |
| `fix_ai_markers.py` | 修复AI标记 |
| `fix_plagiarism.py` | 修复抄袭问题 |

## 使用方式

这些工具被其他skill调用，通常不直接使用：

```powershell
# 拆章
python .agents/skills/story-tools/split_chapters_generic.py <源文> <输出目录>

# 合并章节
python .agents/skills/story-tools/merge_chapters.py <章节目录> <输出文件>

# 修复标题
python .agents/skills/story-tools/fix_chapter_titles.py <章节目录> <源文>
```

## 依赖关系

- `story-engine` 调用：split_chapters, fix_chapter_titles, create_templates, fix_ai_markers, fix_plagiarism
- `story-export` 调用：merge_chapters
- `story-compare` 调用：split_chapters_generic
