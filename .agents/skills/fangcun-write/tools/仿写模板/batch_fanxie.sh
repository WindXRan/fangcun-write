#!/bin/bash
# 批量仿写 — 一键跑全书
# 用法: bash batch_fanxie.sh <仿写项目名> <起始章> <结束章>

PROJECT=$1
START=$2
END=$3

if [ -z "$PROJECT" ]; then
  echo "用法: bash batch_fanxie.sh <仿写项目名> [起始章] [结束章]"
  echo "示例: bash batch_fanxie.sh 仿写新书 1 5    # 跑第1-5章"
  echo "示例: bash batch_fanxie.sh 仿写新书          # 跑全部"
  exit 1
fi

cd "$(dirname "$0")/../../.."

# 读取总章数
TOTAL=$(python3 -c "
import xml.etree.ElementTree as ET
t = ET.parse('projects/$PROJECT/作品信息/project.xml')
print(t.getroot().findtext('total_chapters') or '200')
")

START=${START:-1}
END=${END:-$TOTAL}

echo "仿写项目: $PROJECT"
echo "章节范围: $START ~ $END"
echo ""

for ch in $(seq $START $END); do
  echo "=== 第${ch}章 ==="

  # Step 1: 源文章纲逆推
  python3 -c "
import sys
sys.path.insert(0, '.agents/skills/fangcun-write/tools')
from tool_executor import run_tool
run_tool('source-guide-reverse', {'chapter_number': $ch}, 'projects/全家偷听心声')
" 2>/dev/null

  # Step 2: 复制到仿写项目
  cp -f "projects/全家偷听心声/正文/章纲/第${ch}章.xml" "projects/$PROJECT/正文/章纲/" 2>/dev/null

  # Step 3: guide-convert（如果失败自动重试1次）
  python3 -c "
import sys
sys.path.insert(0, '.agents/skills/fangcun-write/tools')
from tool_executor import run_tool
# 第一次尝试
r = run_tool('guide-convert', {'chapter_number': $ch}, 'projects/$PROJECT')
# 检查输出是否包含模板文字
import re
t = open('projects/$PROJECT/正文/章纲/第${ch}章.xml', encoding='utf-8').read()
if '替换后的功能标题' in t or '核心事件' in t and len(t) < 200:
    print('  模板输出→重试...')
    run_tool('guide-convert', {'chapter_number': $ch}, 'projects/$PROJECT')
" 2>/dev/null

  # Step 4: 写正文
  python3 -c "
import sys
sys.path.insert(0, '.agents/skills/fangcun-write/tools')
from tool_executor import run_tool
run_tool('fanxie-chapter', {'chapter_number': $ch}, 'projects/$PROJECT')
" 2>/dev/null

  # 简单验证
  python3 -c "
import re
t = open('projects/$PROJECT/正文/正文/第${ch}章.xml', encoding='utf-8').read()
m = re.search(r'<content>(.*?)</content>', t, re.DOTALL)
if m:
    c = m.group(1).strip()
    lines = len([l for l in c.split(chr(10)) if l.strip()])
    bad = [n for n in ['乔娇娇','乔夫人','乔忠国','乔天经','乔地义','孟谷雪','冷面王爷轻点宠','功德商城','功德点','老阎王','阎王'] if n in c]
    status = '❌' if bad else '✅'
    print(f'  {status} {lines}行 {len(c)}字')
else:
    print('  ❌ 无正文')
" 2>/dev/null

done

echo ""
echo "全部完成: $START ~ $END"
