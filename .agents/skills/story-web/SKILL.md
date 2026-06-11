---
name: story-web
description: |
  书库 Web 应用。Flask 服务，提供书库浏览、阅读器（支持版本切换）、对比阅读、番茄排行榜分析。
  触发方式：/story-web、/web、「启动书库」「打开阅读器」「web服务」
---

# story-web · 书库 Web 应用

## 启动

```bash
python -m .agents.skills.story-web.app
# 或
python .agents/skills/story-web/app.py
```

默认端口 5000，浏览器访问 http://127.0.0.1:5000/

## 功能

| 页面 | 路由 | 说明 |
|------|------|------|
| 书库首页 | `/` | 所有书籍卡片，支持搜索/筛选/排序 |
| 阅读器 | `/book/<idx>` | 阅读指定书籍，支持源文/仿写版本切换 |
| 对比阅读 | `/compare` | 左右对照两个版本，支持版本选择、章节同步 |
| 扫描书库 | `/scan` | 重新扫描 projects/ 生成索引 |
| 番茄排行榜 | `/ranks/` | 榜单看板、趋势风向、创作灵感 |

## 排行榜功能

排行榜数据由 story-scan 采集和分析，页面统一在 story-web 展示：

| 页面 | 地址 | 说明 |
|------|------|------|
| 榜单看板 | `/ranks/` | 四大榜单（男频新书/畅读、女频新书/畅读） |
| 趋势风向 | `/ranks/trend.html` | 题材趋势、热度变化 |
| 创作灵感 | `/ranks/author.html` | 作者分析、读者画像、创作建议 |

### 数据更新

```bash
# 采集最新数据
cd .agents/skills/story-scan
python run.py scrape

# 构建分析
python run.py build
```

数据自动保存到 `story-web/data/scan/`，无需手动复制。

## API 接口

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/books` | GET | 获取所有书籍列表 |
| `/api/search?q=&genre=` | GET | 搜索书籍 |
| `/api/version_chapters?book_idx=&ver_idx=` | GET | 获取指定版本的章节列表 |
| `/api/chapters?file=` | GET | 获取单文件书籍的章节列表 |
| `/api/content?file=&chapter=` | GET | 获取指定章节内容 |
| `/api/scan` | POST | 扫描书库 |

## 对比阅读功能

对比阅读器支持：
- **版本切换**：选择同一本书的不同版本（源文/仿写）
- **章节同步**：点击"同步章节"按钮，两个面板跳转到同一章节索引
- **同步滚动**：启用后，一个面板滚动会同步另一个面板
- **键盘快捷键**：左/右箭头切换章节，N键切换夜间模式
- **字数统计**：显示每章的字数

## 目录结构

```
.agents/skills/story-web/
├── SKILL.md
├── app.py              # Flask 主应用
├── templates/          # Jinja2 模板
│   ├── index.html      # 书库首页
│   ├── reader.html     # 阅读器（版本切换）
│   ├── compare.html    # 对比阅读
│   ├── scan.html       # 扫描页面
│   └── ...             # 排行榜模板
├── static/             # 静态资源
│   ├── css/
│   ├── js/
│   └── api/            # 番茄排行榜数据
├── tools/
│   └── book_library.py # 书库扫描脚本
└── data/
    └── book_library.json # 书库索引（自动生成）
```

## 扫描脚本

```bash
# 重新生成书库索引
python .agents/skills/story-web/tools/book_library.py scan

# 搜索书籍
python .agents/skills/story-web/tools/book_library.py search "关键词"
```

## 书库索引格式

```json
{
  "updated": "2026-06-10T...",
  "total_books": 31,
  "total_chars": 23596331,
  "genres": { "甜宠": 5, "其他": 20, ... },
  "books": [
    {
      "title": "书名",
      "author": "作者",
      "genre": "题材",
      "char_count": 100000,
      "chapter_count": 500,
      "cover": "projects/作者/书名/_cache/cover.jpg",
      "versions": [
        { "type": "source", "name": "源文", "file": "..." },
        { "type": "rewrite", "name": "仿写名", "chapters": [...] }
      ],
      "version_count": 2
    }
  ]
}
```

## 封面规范

封面保存在 `projects/{作者}/{书名}/_cache/cover.jpg`，下载器自动保存。
扫描时自动检测 `cover.{jpg,jpeg,png,webp}`。

## 与 story-engine 集成

story-engine 的 `pipeline.py` 在写章完成后会自动启动书库服务，方便用户阅读和对比。
