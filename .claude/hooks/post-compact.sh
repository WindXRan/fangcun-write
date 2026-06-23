#!/bin/bash
# post-compact.sh - 上下文压缩后提示恢复上下文

if [ ! -f ".active-book" ]; then
    exit 0
fi

ACTIVE=$(cat .active-book)
SNAPSHOT_DIR="$ACTIVE/_snapshot"

if [ ! -d "$SNAPSHOT_DIR" ]; then
    exit 0
fi

# 找到最新的快照
LATEST=$(ls -t "$SNAPSHOT_DIR"/compact-*.md 2>/dev/null | head -1)

if [ -n "$LATEST" ]; then
    echo ""
    echo "=== 上下文已压缩 ==="
    echo "最新进度快照: $LATEST"
    echo ""
    echo "请读取以下文件恢复上下文:"
    echo "  1. $ACTIVE/concept.md"
    echo "  2. $LATEST"
    echo "========================="
fi
