#!/usr/bin/env bash
# verify-rules/check_tools.sh
# 检测工具使用健康度，输出 TOOL_SIGNAL 信号供 meta-skill-agent 读取
# 用法：bash .claude/hooks/verify-rules/check_tools.sh <project_name>
set -eu

PROJECT="${1:-}"
if [ -z "$PROJECT" ]; then
    FRAMEWORK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
    CLAUDE_MD="$FRAMEWORK_ROOT/CLAUDE.md"
    if [ -f "$CLAUDE_MD" ]; then
        PROJECT=$(grep -E "^PROJECT:" "$CLAUDE_MD" | head -1 | sed 's/PROJECT://' | tr -d ' ')
    fi
fi

if [ -z "$PROJECT" ] || [ "$PROJECT" = "none" ]; then
    echo "⚠️  未检测到激活项目，跳过 tool health check"
    exit 0
fi

FRAMEWORK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
PROJECT_DIR="$FRAMEWORK_ROOT/projects/$PROJECT"
SESSIONS_DIR="$PROJECT_DIR/memory/sessions"
PLAN_JSON="$PROJECT_DIR/docs/plan.json"
HANDOFF="$PROJECT_DIR/HANDOFF.json"

echo ""
echo "=== Tool Health Check: $PROJECT ==="

WARN=0

# ── 检测 1：HANDOFF.json 孤儿 ─────────────────────────────────────────────────
if [ -f "$HANDOFF" ]; then
    if command -v stat &>/dev/null; then
        # macOS
        MOD_TIME=$(stat -f %m "$HANDOFF" 2>/dev/null || stat -c %Y "$HANDOFF" 2>/dev/null || echo 0)
        NOW=$(date +%s)
        AGE=$(( (NOW - MOD_TIME) / 3600 ))
        if [ "$AGE" -gt 24 ]; then
            echo "TOOL_SIGNAL: handoff_orphan project=$PROJECT age=${AGE}h"
            echo "  → handoff.py read 可能被跳过，建议在启动协议里强制执行 read+clear"
            WARN=$((WARN+1))
        else
            echo "  ✅ HANDOFF.json 存在且新鲜（${AGE}h 内）"
        fi
    fi
fi

# ── 检测 2：plan.json 中停滞的 in_progress 模块 ──────────────────────────────
if [ -f "$PLAN_JSON" ]; then
    STALE=$(python3 -c "
import json, sys
try:
    p = json.load(open('$PLAN_JSON'))
    stale = [m['name'] for b in p.get('batches',[]) for m in b.get('modules',[]) if m.get('state') == 'in_progress']
    print(','.join(stale))
except Exception as e:
    pass
" 2>/dev/null || true)
    if [ -n "$STALE" ]; then
        echo "TOOL_SIGNAL: stale_in_progress project=$PROJECT modules=$STALE"
        echo "  → plan-tracker 缺少 stale-detection 功能，模块停留在 in_progress 超过预期"
        WARN=$((WARN+1))
    else
        echo "  ✅ 无停滞模块（in_progress 状态正常）"
    fi
fi

# ── 检测 3：session-snapshot 写入频率异常 ─────────────────────────────────────
if [ -d "$SESSIONS_DIR" ]; then
    LATEST=$(ls -t "$SESSIONS_DIR"/*.md 2>/dev/null | head -1 || true)
    if [ -n "$LATEST" ]; then
        CP_COUNT=$(grep -c "\[CHECKPOINT" "$LATEST" 2>/dev/null || echo 0)
        LINE_COUNT=$(wc -l < "$LATEST" 2>/dev/null || echo 0)
        # 超过 80 行（约 10 轮对话）但少于 2 个 CHECKPOINT → 触发率异常
        if [ "$LINE_COUNT" -gt 80 ] && [ "$CP_COUNT" -lt 2 ]; then
            echo "TOOL_SIGNAL: sparse_checkpoints project=$PROJECT file=$(basename $LATEST) cp=$CP_COUNT lines=$LINE_COUNT"
            echo "  → session-snapshot 触发阈值可能过高，或 CHECKPOINT 触发条件未生效"
            WARN=$((WARN+1))
        else
            echo "  ✅ session-snapshot 写入频率正常（${CP_COUNT} checkpoints / ${LINE_COUNT} lines）"
        fi
    fi
fi

# ── 检测 4：candidates/ 积压检查 ──────────────────────────────────────────────
CANDIDATES_DIR="$FRAMEWORK_ROOT/memory/candidates"
if [ -d "$CANDIDATES_DIR" ]; then
    PENDING=$(find "$CANDIDATES_DIR" -name "*.yaml" | xargs grep -l "status: pending_review" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$PENDING" -gt 10 ]; then
        echo "TOOL_SIGNAL: candidate_backlog count=$PENDING"
        echo "  → 积压 $PENDING 条待审核候选，建议运行 /project:skill-review"
        WARN=$((WARN+1))
    else
        echo "  ✅ 候选积压正常（${PENDING} 条 pending）"
    fi
fi

# ── 检测 5：skill-changelog.md 存在性 ─────────────────────────────────────────
CHANGELOG="$FRAMEWORK_ROOT/memory/skill-changelog.md"
if [ ! -f "$CHANGELOG" ]; then
    echo "TOOL_SIGNAL: missing_changelog"
    echo "  → memory/skill-changelog.md 不存在，SKILL 版本历史无法追踪"
    WARN=$((WARN+1))
else
    echo "  ✅ skill-changelog.md 存在"
fi

echo ""
echo "=== Tool Health 结果：${WARN} 个警告 ==="
echo ""
