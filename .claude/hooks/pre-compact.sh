#!/bin/bash
# pre-compact.sh - 上下文压缩前保存进度快照

if [ ! -f ".active-book" ]; then
    exit 0
fi

ACTIVE=$(cat .active-book)
SNAPSHOT_DIR="$ACTIVE/_snapshot"
mkdir -p "$SNAPSHOT_DIR"

SNAPSHOT_FILE="$SNAPSHOT_DIR/compact-$(date '+%Y%m%d-%H%M%S').md"

echo "# 进度快照" > "$SNAPSHOT_FILE"
echo "" >> "$SNAPSHOT_FILE"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$SNAPSHOT_FILE"
echo "" >> "$SNAPSHOT_FILE"

# 记录当前章节进度
chapters=$(find "$ACTIVE/chapters" -name "ch_*.txt" 2>/dev/null | wc -l)
echo "已完成章节: $chapters" >> "$SNAPSHOT_FILE"

# 记录最新章节内容摘要
latest=$(ls -t "$ACTIVE/chapters"/ch_*.txt 2>/dev/null | head -1)
if [ -n "$latest" ]; then
    echo "" >> "$SNAPSHOT_FILE"
    echo "最新章节: $(basename $latest)" >> "$SNAPSHOT_FILE"
    echo "摘要:" >> "$SNAPSHOT_FILE"
    head -20 "$latest" >> "$SNAPSHOT_FILE"
fi

echo ""
echo "进度快照已保存: $SNAPSHOT_FILE"
