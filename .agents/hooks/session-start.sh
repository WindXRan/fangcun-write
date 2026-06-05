#!/bin/bash
# session-start.sh — 显示项目状态和写作上下文摘要
# 设计原则：无可用信息时完全静默，不输出任何内容，避免污染 context
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT=""
HAS_CONTENT=false

# 先做最小 preflight，再 source；否则 lib 缺失时无法输出可修复提示。
if [ ! -f "$HOOK_DIR/lib/common.sh" ]; then
  printf '%b' "[WARN] story hook libraries are missing. Re-run /story-setup to restore .claude/hooks/lib/.\n"
  exit 0
fi

# 加载公共函数库
source "$HOOK_DIR/lib/common.sh"


ROOT=$(project_root)



# 显示分支和最近 commit（仅在有 git 历史时）
BRANCH=$(git -C "$ROOT" branch --show-current 2>/dev/null || echo "")
if [ -n "$BRANCH" ]; then
  OUTPUT+="=== Story Writing ===\n"
  OUTPUT+="Branch: $BRANCH\n"
  RECENT=$(git -C "$ROOT" log --oneline -5 2>/dev/null || true)
  if [ -n "$RECENT" ]; then
    OUTPUT+="$RECENT\n"
  fi
  OUTPUT+="\n"
  HAS_CONTENT=true
fi

# 上下文.md 摘要（只看当前位置部分，前 10 行）
BOOK_DIR=$(discover_active_book)
if [ -n "$BOOK_DIR" ] && [ -f "$BOOK_DIR/追踪/上下文.md" ]; then
  OUTPUT+="--- 当前位置 ---\n"
  SNAPSHOT=$(head -10 "$BOOK_DIR/追踪/上下文.md")
  OUTPUT+="${SNAPSHOT}\n---\n\n"
  HAS_CONTENT=true
fi

# 未完成拆文（阈值 > 0 才报告）
if [ -d "$ROOT/拆文库" ]; then
  PROGRESS_COUNT=$(find "$ROOT/拆文库" -name "_progress.md" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$PROGRESS_COUNT" -gt 0 ]; then
    OUTPUT+="[INFO] $PROGRESS_COUNT incomplete analysis in 拆文库/. Run /story-long-analyze or /story-short-analyze.\n"
    HAS_CONTENT=true
  fi
fi

# 仅在有实际内容时输出，否则完全静默
if [ "$HAS_CONTENT" = true ]; then
  printf '%b' "$OUTPUT"
fi
