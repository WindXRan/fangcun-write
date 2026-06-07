#!/bin/bash
# count-words.sh — 番茄标准字数统计
# 番茄标准：所有非空格字符（汉字+标点+数字+英文）
# 用法: count-words.sh <文件路径>

FILE="$1"

if [ ! -f "$FILE" ]; then
  echo "文件不存在: $FILE"
  exit 1
fi

# 番茄标准：删除所有空格和换行后计算字符数
TOTAL=$(tr -d '[:space:]' < "$FILE" | wc -m | tr -d ' ')

echo "番茄字数: $TOTAL"

if [ "$TOTAL" -lt 2000 ]; then
  echo "⚠️ 字数不足: $TOTAL < 2000"
elif [ "$TOTAL" -gt 3000 ]; then
  echo "⚠️ 字数超标: $TOTAL > 3000"
else
  echo "✅ 字数合格"
fi
