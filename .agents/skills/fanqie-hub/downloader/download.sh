#!/bin/bash
# 番茄小说下载器 — 固定流程
# 用法: ./download.sh "书名"
# 依赖: 下载器server已在后台运行 (端口18423)

set -e

BOOK_NAME="$1"
if [ -z "$BOOK_NAME" ]; then
  echo "用法: $0 \"书名\""
  exit 1
fi

BASE_URL="http://127.0.0.1:18423"
DOWNLOAD_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🔍 搜索: $BOOK_NAME"

# 1. 搜索
SEARCH_RESULT=$(curl -s "$BASE_URL/api/search?q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$BOOK_NAME'))")")
BOOK_ID=$(echo "$SEARCH_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = data.get('items', [])
for b in items:
    title = b.get('title', b.get('book_name', ''))
    bid = b.get('book_id', '')
    if '$BOOK_NAME' in title:
        print(bid)
        sys.exit(0)
# fallback: print first result
if items:
    print(items[0].get('book_id', ''))
")

if [ -z "$BOOK_ID" ]; then
  echo "❌ 未找到书"
  exit 1
fi

BOOK_TITLE=$(echo "$SEARCH_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for b in data.get('items', []):
    if b.get('book_id', '') == '$BOOK_ID':
        print(b.get('title', b.get('book_name', '?')))
" 2>/dev/null || echo "$BOOK_NAME")

echo "📖 找到: $BOOK_TITLE (ID: $BOOK_ID)"

# 2. 开始下载
echo "⏳ 开始下载..."
JOB_RESULT=$(curl -s -X POST "$BASE_URL/api/jobs" \
  -H "Content-Type: application/json" \
  -d "{\"book_id\":\"$BOOK_ID\"}")

JOB_ID=$(echo "$JOB_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))")
echo "📝 任务ID: $JOB_ID"

# 3. 等待完成
while true; do
  JOBS=$(curl -s "$BASE_URL/api/jobs")
  STATE=$(echo "$JOBS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for j in data.get('items', []):
    if j.get('id') == $JOB_ID:
        s = j['state']
        p = j.get('progress', {})
        ch = f\"{p.get('saved_chapters',0)}/{p.get('chapter_total','?')}\"
        print(f'{s}|{ch}')
        sys.exit(0)
print('completed|done')
" 2>/dev/null)

  STATE_VAL=$(echo "$STATE" | cut -d'|' -f1)
  PROGRESS=$(echo "$STATE" | cut -d'|' -f2)

  if [ "$STATE_VAL" = "completed" ] || [ "$STATE_VAL" = "done" ]; then
    echo "✅ 下载完成! ($PROGRESS)"
    break
  elif [ "$STATE_VAL" = "failed" ]; then
    echo "❌ 下载失败"
    exit 1
  else
    echo "⏳ 进度: $PROGRESS"
    sleep 5
  fi
done

# 4. 提取为txt文件
echo "📂 提取章节..."
OUT_DIR="$DOWNLOAD_DIR/$BOOK_ID"
CHAPTERS_FILE="$OUT_DIR/downloaded_chapters.jsonl"

if [ -f "$CHAPTERS_FILE" ]; then
  python3 << EOF
import json, os, re

out_dir = "$OUT_DIR"
chapters_file = "$CHAPTERS_FILE"

# 清理html标签
def clean_html(text):
    text = re.sub(r'<p>', '\n', text)
    text = re.sub(r'</p>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    return text.strip()

with open(chapters_file, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            ch = json.loads(line)
            title = ch.get('title', f'第{ch.get("chapter_num", "?")}章')
            content = ch.get('content', ch.get('text', ''))
            if not content:
                continue
            content = clean_html(content)
            # get chapter number for sorting
            ch_num = ch.get('chapter_num', 0)
            filename = f'{ch_num:04d}_{title}.txt'
            # sanitize filename
            filename = re.sub(r'[\\/:*?\"<>|]', '', filename)
            filepath = os.path.join(out_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as cf:
                cf.write(f'$title\n\n{content}\n')
        except:
            pass

print("提取完成")
EOF
  echo "📁 文件保存在: $OUT_DIR"
  ls "$OUT_DIR"/*.txt 2>/dev/null | head -5
  echo "...共 $(ls "$OUT_DIR"/*.txt 2>/dev/null | wc -l) 章"
else
  echo "⚠️ 章节文件不存在，检查下载目录"
fi
