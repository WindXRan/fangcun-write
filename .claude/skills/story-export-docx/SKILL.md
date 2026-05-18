---
name: story-export-docx
version: 1.0.0
description: |
  小说正文导出为 Word 文档。将项目中的正文.md 转换为编辑可直接收稿的 .docx 文件。
  触发方式：/story-export-docx、/导出、「导出word」「导出docx」「做成word」「生成word」
metadata:
  requires:
    bins:
      - python3
    packages:
      - python-docx
  source: project
---

# story-export-docx：正文导出 Word

你是小说稿件导出工具。读取项目中的正文文件，生成编辑可直接收稿的标准 Word 文档。

**核心原则：纯正文，零多余。编辑只要故事，不要标题页、署名、字数统计、原创声明。**

---

## 输入识别

```
用户指定了哪个项目？
├─ 指定了书名/路径 → 定位到 {书名}/正文/
├─ 当前在项目目录中 → 使用当前目录
└─ 都没指定 → 问用户要导出的项目名
```

正文源文件查找优先级：
1. `正文.md`（短篇单文件）
2. `正文/第001章_*.md` `正文/第002章_*.md` ...（长篇多文件）
3. 找不到 → 报错

---

## Word 格式规范

### 页面
- A4，上下边距 2.54cm，左右边距 3.18cm
- 默认字体：宋体 12pt，1.5 倍行距

### 内容层次

**导语**（如果正文开头有独立于第 1 节之外的文字）：
- 作为正文开篇，不加「导语」标签
- 宋体 12pt，与正文格式一致

**节号**（1、2、3...）：
- 独立一行，宋体 12pt 加粗
- 段前 12pt 间距

**正文段落**：
- 一句一段，宋体 12pt
- 段前段后均为 0

**系统/弹幕消息**（【...】格式）：
- 宋体 10.5pt，灰色（RGB 100,100,100）
- 不斜体、不加粗

**番外**：
- 「番外」二字独立一行，宋体 12pt 加粗
- 番外内的数字条目（如 `1.` `2.`）加粗

**全文完**：
- 「（全文完）」居中，宋体 12pt
- 段前 8pt 间距

### 禁止内容
- 不要标题页
- 不要署名/作者名
- 不要字数统计
- 不要题材标签
- 不要【导语】【正文】标签
- 不要原创声明/版权声明
- 不要分隔线
- 不要页眉页脚

---

## 执行流程

### 1. 检查依赖

```bash
python3 -c "import docx; print('OK')" 2>&1 || pip install python-docx
```

### 2. 读取正文

定位正文文件，读取全部内容。

### 3. 解析结构

按以下规则解析：
- `###N.` 或 `###N。` → 节号（N 为数字）
- `番外`（独立一行）→ 番外标记
- `【全文完】` → 结束标记
- `【...】` 格式的行 → 系统/弹幕消息
- 其余为正文段落

### 4. 生成 docx

使用 python-docx 按格式规范逐段写入。导语 → 节号 → 正文段落 → 番外 → 全文完。

### 5. 输出

文件保存到项目目录下：`{书名}.docx`（与正文同级）。

---

## 转换脚本模板

```python
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import re

doc = Document()

for sec in doc.sections:
    sec.top_margin = Cm(2.54)
    sec.bottom_margin = Cm(2.54)
    sec.left_margin = Cm(3.18)
    sec.right_margin = Cm(3.18)

style = doc.styles['Normal']
style.font.name = '宋体'
style.font.size = Pt(12)
style.paragraph_format.line_spacing = 1.5
rPr = style.element.get_or_add_rPr()
rFonts = rPr.makeelement(qn('w:rFonts'), {})
rFonts.set(qn('w:eastAsia'), '宋体')
rPr.insert(0, rFonts)

def add_p(text, size=12, bold=False, color=None, align=None, before=0):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(0)
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.name = '宋体'
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.makeelement(qn('w:rFonts'), {})
    rFonts.set(qn('w:eastAsia'), '宋体')
    rPr.insert(0, rFonts)
    if color:
        run.font.color.rgb = color

# Read content
with open('正文.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Split by ###N.
parts = re.split(r'###(\d+)\.', content)

# 导语
daoyu = parts[0].strip()
for line in daoyu.split('\n'):
    line = line.strip()
    if line:
        add_p(line)

add_p('', size=12)

# Sections
i = 1
while i < len(parts):
    num = parts[i]
    text = parts[i+1].strip()
    i += 2

    add_p(num, size=12, bold=True, before=12)

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        if line.startswith('番外'):
            add_p('', size=12, before=8)
            add_p('番外', size=12, bold=True, before=8)
            continue

        if '【全文完】' in line:
            add_p('', size=12, before=8)
            add_p('（全文完）', size=12, align=WD_ALIGN_PARAGRAPH.CENTER, before=8)
            continue

        if re.match(r'【[^】]+】', line):
            add_p(line, size=10.5, color=RGBColor(100,100,100))
            continue

        add_p(line, size=12)

doc.save('{书名}.docx')
```

---

## 多文件长篇处理

如果正文是多个文件（`正文/第001章_*.md` 等），按章节顺序合并后再执行上述转换。每章开头插入章标题（如「第一章 xxx」加粗）作为分隔。

---

## 语言

跟随用户语言回复。中文遵循《中文文案排版指北》。
