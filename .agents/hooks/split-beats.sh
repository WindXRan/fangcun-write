#!/bin/bash
# split-beats.sh — 拆分源文章节为节拍，统计每段字数
# 用法: split-beats.sh <源文路径> <节拍数>
# 输出: 每个节拍的字数和占比

FILE="$1"
BEATS="$2"

if [ ! -f "$FILE" ]; then
  echo "文件不存在: $FILE"
  exit 1
fi

# 番茄标准总字数
TOTAL=$(tr -d '[:space:]' < "$FILE" | wc -m | tr -d ' ')
echo "源文总字数: $TOTAL"
echo "节拍数: $BEATS"
echo "---"

# 计算每个节拍的字数（按段落平均分配）
LINES=$(wc -l < "$FILE" | tr -d ' ')
LINES_PER_BEAT=$((LINES / BEATS))

for i in $(seq 1 $BEATS); do
  START=$(( (i-1) * LINES_PER_BEAT + 1 ))
  if [ $i -eq $BEATS ]; then
    END=$LINES
  else
    END=$(( i * LINES_PER_BEAT ))
  fi
  
  BEAT_CHARS=$(sed -n "${START},${END}p" "$FILE" | tr -d '[:space:]' | wc -m | tr -d ' ')
  PCT=$(( BEAT_CHARS * 100 / TOTAL ))
  
  echo "节拍$i: ${BEAT_CHARS}字 (${PCT}%)"
done
