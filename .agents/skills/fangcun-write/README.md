# fangcun-novel 仿写引擎

## 这是什么？

从小说源文自动生成仿写版本。保留情绪弧线和叙事骨架，换掉人名、地名、具体情节。

## 快速开始

### 1. 安装依赖

```powershell
.\setup.ps1
```

### 2. 设置 API Key

```powershell
$env:API_KEY = "sk-xxx"
```

### 3. 准备源文

把源文 txt 放到：
```
projects/{作者名}/{源书名}/original.txt
```

### 4. 创建配置

```powershell
copy configs\example.json configs\mybook.json
notepad configs\mybook.json
```

编辑配置：
```json
{
  "book_name": "我的新书",
  "author": "源文作者",
  "source_book": "源文书名",
  "rewrites_dir": "projects/源文作者/源文书名/rewrites/我的新书"
}
```

### 5. 开始仿写

```powershell
# 写前 10 章
.\novel.ps1 write --config configs\mybook.json --start 1 --end 10

# 查看状态
.\novel.ps1 status --config configs\mybook.json

# 对比审核
.\novel.ps1 compare --config configs\mybook.json --start 1 --end 10
```

---

## 命令

| 命令 | 说明 |
|------|------|
| `.\novel.ps1 write` | 写章 |
| `.\novel.ps1 compare` | 对比审核 |
| `.\novel.ps1 status` | 查看状态 |
| `.\novel.ps1 export` | 导出 TXT |

### 参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--config` | 配置文件路径 | `--config configs\mybook.json` |
| `--start` | 起始章 | `--start 1` |
| `--end` | 结束章 | `--end 10` |
| `--workers` | 并行数 | `--workers 10` |

---

## 输出结构

```
projects/{作者}/{源书名}/rewrites/{新书名}/
├── concept.md             ← 设定
├── characters.md          ← 角色映射表
├── guides/plot_{N}.md     ← 章纲
├── chapters/ch_{N}.txt    ← 正文
├── compare/               ← 对比报告
└── export/                ← 导出文件
```

---

## 常见问题

**Q: API Key 错误**
```powershell
$env:API_KEY = "sk-xxx"
```

**Q: 某章写得不好**
```powershell
Remove-Item chapters\ch_003.txt
.\novel.ps1 write --config configs\mybook.json --start 3 --end 3
```

**Q: 字数超标**
trim 会自动执行。如果还是超，重跑该章。

**Q: 角色名不对**
编辑 `characters.md`，然后重跑受影响的章节。

---

## 技术架构

```
style-analyze（文笔层）    → 提取源文写法特征
plot-guide（结构层）       → 生成功能需求清单
write-chapter（执行层）    → 按功能需求写全新内容
```

职责分离：
- style-analyze 只管怎么写（句长、对话比、写法指令）
- plot-guide 只管写什么（情绪功能、冲突升级、信息流）
- write-chapter 按功能需求写全新场景
