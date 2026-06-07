#!/bin/bash
# calc-beats.sh — 根据源文字数计算新书每个节拍的字数
# 用法: calc-beats.sh <源文字数> <节拍数> <节拍占比列表(逗号分隔)>
# 示例: calc-beats.sh 2000 5 "20,25,30,15,10"

SOURCE_TOTAL="$1"
BEATS="$2"
PCTS="$3"

if [ -z "$SOURCE_TOTAL" ] || [ -z "$BEATS" ] || [ -z "$PCTS" ]; then
  echo "用法: calc-beats.sh <源文字数> <节拍数> <节拍占比列表>"
  echo "示例: calc-beats.sh 2000 5 '20,25,30,15,10'"
  exit 1
fi

# 新书字数 = 源文 × 1.1（多10%）
NEW_TOTAL=$(( SOURCE_TOTAL * 11 / 10 ))

echo "源文字数: $SOURCE_TOTAL"
echo "新书目标: $NEW_TOTAL (×1.1)"
echo "---"

# 按占比分配
IFS=',' read -ra PCT_ARRAY <<< "$PCTS"
ALLOCATED=0

for i in "${!PCT_ARRAY[@]}"; do
  PCT=${PCT_ARRAY[$i]}
  BEAT_CHARS=$(( NEW_TOTAL * PCT / 100 ))
  ALLOCATED=$(( ALLOCATED + BEAT_CHARS ))
  echo "节拍$((i+1)): ${PCT}% → ${BEAT_CHARS}字"
done

echo "---"
echo "已分配: $ALLOCATED字"
echo "剩余: $((NEW_TOTAL - ALLOCATED))字"
