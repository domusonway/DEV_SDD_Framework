#!/usr/bin/env bash
# verify-rules/check.sh
# 验证 SDD Rules 系统今日是否正常运行
# 用法：bash .claude/hooks/verify-rules/check.sh
# 建议：每天工作结束后手动执行一次

set -eu

# ── 读取当前激活项目 ──────────────────────────────────────────────────────────
FRAMEWORK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
CLAUDE_MD="$FRAMEWORK_ROOT/CLAUDE.md"

PROJECT=""
if [ -f "$CLAUDE_MD" ]; then
    PROJECT=$(grep -E "^PROJECT:" "$CLAUDE_MD" | head -1 | sed 's/PROJECT://' | tr -d ' ')
fi

if [ -z "$PROJECT" ] || [ "$PROJECT" = "none" ]; then
    echo "⚠️  未检测到激活项目，请先执行 /project:switch"
    exit 1
fi

SESSION_DIR="$FRAMEWORK_ROOT/projects/$PROJECT/memory/sessions"
TODAY=$(date +%Y-%m-%d)

echo ""
echo "═══════════════════════════════════════════"
echo "  SDD Rules 验证报告"
echo "  项目: $PROJECT  日期: $TODAY"
echo "═══════════════════════════════════════════"
echo ""

PASS=0
WARN=0
FAIL=0

# ── 检查 1：今日是否有 session 文件 ──────────────────────────────────────────
echo "【1】今日 session 记录"
if [ ! -d "$SESSION_DIR" ]; then
    echo "  ❌ sessions/ 目录不存在，请创建: $SESSION_DIR"
    FAIL=$((FAIL+1))
elif ls "$SESSION_DIR"/${TODAY}_*.md 2>/dev/null | head -1 | grep -q .; then
    SESSION_COUNT=$(ls "$SESSION_DIR"/${TODAY}_*.md 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ 今日有 $SESSION_COUNT 个 session 文件"
    PASS=$((PASS+1))
else
    echo "  ❌ 今日无 session 记录（Rules 可能未生效，或今日未开发）"
    FAIL=$((FAIL+1))
fi

# ── 检查 2：session 是否正常关闭 ─────────────────────────────────────────────
echo ""
echo "【2】会话关闭状态"
if [ -d "$SESSION_DIR" ] && ls "$SESSION_DIR"/${TODAY}_*.md 2>/dev/null | head -1 | grep -q .; then
    LATEST=$(ls -t "$SESSION_DIR"/${TODAY}_*.md | head -1)
    if grep -q "status: completed" "$LATEST" 2>/dev/null; then
        echo "  ✅ 最新会话已正常关闭（包含 SESSION-END）"
        PASS=$((PASS+1))
    elif grep -q "status: in-progress" "$LATEST" 2>/dev/null; then
        echo "  ⚠️  最新会话未关闭（status: in-progress）"
        echo "      → 可能是对话意外中断，下次启动会自动提示续接"
        WARN=$((WARN+1))
    fi
else
    echo "  ─  无 session 文件，跳过"
fi

# ── 检查 3：检查点数量 ────────────────────────────────────────────────────────
echo ""
echo "【3】检查点记录"
if [ -d "$SESSION_DIR" ] && ls "$SESSION_DIR"/${TODAY}_*.md 2>/dev/null | head -1 | grep -q .; then
    TOTAL_CP=0
    for f in "$SESSION_DIR"/${TODAY}_*.md; do
        CP=$(grep -c "\[CHECKPOINT" "$f" 2>/dev/null || echo 0)
        TOTAL_CP=$((TOTAL_CP + CP))
    done
    if [ "$TOTAL_CP" -gt 0 ]; then
        echo "  ✅ 今日共 $TOTAL_CP 个检查点"
        PASS=$((PASS+1))
    else
        echo "  ⚠️  今日无检查点记录（开发过程未被捕获）"
        echo "      → 检查 Rules 中 CHECKPOINT 触发条件是否正确配置"
        WARN=$((WARN+1))
    fi
else
    echo "  ─  无 session 文件，跳过"
fi

# ── 检查 4：memory/ 文件近期有无更新 ─────────────────────────────────────────
echo ""
echo "【4】记忆库近期活跃度"
MEMORY_DIR="$FRAMEWORK_ROOT/projects/$PROJECT/memory"
if [ -d "$MEMORY_DIR" ]; then
    RECENT=$(find "$MEMORY_DIR" -name "*.md" -newer "$CLAUDE_MD" 2>/dev/null | grep -v sessions | wc -l | tr -d ' ')
    if [ "$RECENT" -gt 0 ]; then
        echo "  ✅ 有 $RECENT 个 memory 文件近期有更新"
        PASS=$((PASS+1))
    else
        echo "  ⚠️  memory/ 近期无更新（正常开发中应有沉淀）"
        WARN=$((WARN+1))
    fi
else
    echo "  ❌ projects/$PROJECT/memory/ 目录不存在"
    FAIL=$((FAIL+1))
fi

# ── 检查 5：PLAN.md 是否同步 ─────────────────────────────────────────────────
echo ""
echo "【5】PLAN.md 同步状态"
PLAN_FILE="$FRAMEWORK_ROOT/projects/$PROJECT/docs/PLAN.md"
if [ -f "$PLAN_FILE" ]; then
    UNCHECKED=$(grep -c "- \[ \]" "$PLAN_FILE" 2>/dev/null || echo 0)
    CHECKED=$(grep -c "- \[x\]" "$PLAN_FILE" 2>/dev/null || echo 0)
    echo "  ✅ PLAN.md 存在  已完成: $CHECKED  待完成: $UNCHECKED"
    PASS=$((PASS+1))
else
    echo "  ─  docs/PLAN.md 不存在（L 模式项目正常）"
fi

# ── 汇总 ─────────────────────────────────────────────────────────────────────
echo ""
echo "───────────────────────────────────────────"
echo "  结果: ✅ $PASS 项通过  ⚠️  $WARN 项警告  ❌ $FAIL 项失败"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "  → 有失败项，请检查 Rules 配置是否正确应用"
    echo "    参考: docs/PROJECT_RULES.md"
elif [ "$WARN" -gt 0 ]; then
    echo "  → 有警告项，系统基本运行但存在记录缺失"
    echo "    建议：在结束工作前主动说"收工"让 Rules 触发 SESSION-END"
else
    echo "  → 系统运行正常，记录完整 🎉"
fi

echo "═══════════════════════════════════════════"
echo ""
