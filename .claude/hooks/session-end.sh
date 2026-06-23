#!/bin/bash
# session-end.sh - 会话结束时记录日志

LOG_FILE="追踪/session-log.txt"
mkdir -p "$(dirname "$LOG_FILE")"

echo "---" >> "$LOG_FILE"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "分支: $(git branch --show-current 2>/dev/null)" >> "$LOG_FILE"

if [ -f ".active-book" ]; then
    echo "活跃项目: $(cat .active-book)" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
