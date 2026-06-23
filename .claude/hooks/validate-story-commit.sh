#!/bin/bash
# validate-story-commit.sh - git commit时检查

# 检查是否有硬编码的API key
if git diff --cached --name-only | xargs grep -l "sk-" 2>/dev/null; then
    echo "⚠️  检测到可能的API key，请检查"
fi

# 检查是否有硬编码的路径
if git diff --cached --name-only | xargs grep -l "C:\\\\" 2>/dev/null; then
    echo "⚠️  检测到Windows硬编码路径，请检查"
fi

# 检查是否有未处理的placeholder
if git diff --cached --name-only | xargs grep -l "{xxx}" 2>/dev/null; then
    echo "⚠️  检测到未替换的placeholder，请检查"
fi
