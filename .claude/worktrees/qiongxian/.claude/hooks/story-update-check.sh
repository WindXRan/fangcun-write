#!/usr/bin/env bash
# 检查 oh-story-claudecode 上游是否有更新
# 用法: bash .claude/hooks/story-update-check.sh

set -euo pipefail

UPSTREAM="upstream"
BRANCH="main"

echo "=== 网文工具箱更新检查 ==="
echo "上游: https://github.com/worldwonderer/oh-story-claudecode"
echo ""

# 1. 拉取上游最新
echo "[1/3] 拉取上游最新..."
git fetch "$UPSTREAM" "$BRANCH" 2>&1 || {
  echo "错误: 无法连接到上游仓库。请检查网络。"
  exit 1
}

# 2. 比较 CHANGELOG
echo "[2/3] CHANGELOG 变化:"
LOCAL_DEPLOYED=$(cat .story-deployed 2>/dev/null | head -5)
echo "  当前部署状态:"
echo "$LOCAL_DEPLOYED" | sed 's/^/    /'

echo ""
echo "  上游最近 10 次提交:"
git log "${UPSTREAM}/${BRANCH}" --oneline -10 | sed 's/^/    /'

echo ""
echo "  上游 CHANGELOG 预览 (前30行):"
git show "${UPSTREAM}/${BRANCH}:CHANGELOG.md" 2>/dev/null | head -30 | sed 's/^/    /' || echo "    (无法读取 CHANGELOG)"

# 3. 模板文件变化
echo ""
echo "[3/3] 模板/Agent/Hook 文件变化 (最近10条):"
git log "${UPSTREAM}/${BRANCH}" --oneline -- "skills/story-setup/references/templates/**" -10 | sed 's/^/    /'
echo ""

echo "=== 检查完成 ==="
echo ""
echo "如果上游有更新，运行 /story-setup 部署最新版本。"
echo "部署后提交: git add -A && git commit -m 'Update: sync upstream tools'"
