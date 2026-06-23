#!/bin/bash
# detect-story-gaps.sh - 检测设定缺口、大纲缺失、伏笔断线

if [ ! -f ".active-book" ]; then
    exit 0
fi

ACTIVE=$(cat .active-book)
PROJECT_DIR="$ACTIVE"

if [ ! -d "$PROJECT_DIR" ]; then
    exit 0
fi

echo "=== 检测设定缺口 ==="

# 检查concept.md是否存在
if [ ! -f "$PROJECT_DIR/concept.md" ]; then
    echo "⚠️  缺少 concept.md（设定文件）"
fi

# 检查章纲是否完整
chapters=$(find "$PROJECT_DIR/chapters" -name "ch_*.txt" 2>/dev/null | wc -l)
guides=$(find "$PROJECT_DIR/guides" -name "plot_*.md" 2>/dev/null | wc -l)

if [ "$chapters" -gt 0 ] && [ "$guides" -eq 0 ]; then
    echo "⚠️  有正文但无章纲"
fi

# 检查compare目录
if [ ! -d "$PROJECT_DIR/compare" ]; then
    echo "⚠️  缺少对比报告目录"
fi

echo "========================="
