#!/bin/bash
# guard-outline-before-prose.sh - 写正文前检查是否有对应章纲

# 这个hook会在创建正文文件时检查是否有对应的章纲
# 如果没有章纲，会阻止创建正文

if [ ! -f ".active-book" ]; then
    exit 0
fi

ACTIVE=$(cat .active-book)

# 检查是否是创建正文文件
if [[ "$1" == *"/chapters/ch_"*".txt" ]]; then
    # 提取章节号
    filename=$(basename "$1")
    chapter_num=$(echo "$filename" | sed -n 's/ch_\([0-9]*\)\.txt/\1/p')
    
    # 检查是否有对应的章纲
    guide_file="$ACTIVE/guides/plot_${chapter_num}.md"
    
    if [ ! -f "$guide_file" ]; then
        echo ""
        echo "⚠️  缺少章纲文件: $guide_file"
        echo "请先创建章纲再写正文"
        echo ""
        exit 1
    fi
fi
