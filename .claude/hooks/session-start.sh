#!/bin/bash
# session-start.sh - 会话开始时显示项目状态

echo "=== 方寸仿写引擎 ==="
echo ""

# 显示当前分支
if git rev-parse --git-dir > /dev/null 2>&1; then
    branch=$(git branch --show-current 2>/dev/null)
    echo "分支: $branch"
fi

# 显示活跃项目
if [ -f ".active-book" ]; then
    active=$(cat .active-book)
    echo "活跃项目: $active"
fi

# 显示项目进度
if [ -d "projects" ]; then
    for project in projects/*/rewrites/*/; do
        if [ -d "$project" ]; then
            chapters=$(find "$project/chapters" -name "ch_*.txt" 2>/dev/null | wc -l)
            guides=$(find "$project/guides" -name "plot_*.md" 2>/dev/null | wc -l)
            echo "  $(basename $(dirname $project))/$(basename $project): ${chapters}章, ${guides}个章纲"
        fi
    done
fi

echo ""
echo "========================="
