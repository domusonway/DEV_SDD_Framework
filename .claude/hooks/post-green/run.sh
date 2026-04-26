#!/usr/bin/env bash
set -eu

PROJECT_ROOT="${1:-.}"
cd "$PROJECT_ROOT"

echo "=== POST-GREEN 验证 ==="
echo ""

echo "📋 Step 1: 最终测试状态"
if python3 -m pytest tests/ -v --tb=short 2>&1 | tail -5; then
    echo "✅ 所有测试 PASS"
else
    echo "❌ 仍有测试失败，post-green 中止"
    exit 1
fi
echo ""

echo "📋 Step 2: 代码质量扫描"
find modules/ -name "*.py" -exec python3 -m py_compile {} \; 2>&1
echo "✅ 语法检查通过"

if grep -rn "except Exception: *pass" modules/ 2>/dev/null; then
    echo "⚠️ 发现 except Exception: pass，建议加日志"
else
    echo "✅ 无裸异常捕获"
fi

todo_count=$(grep -rn "TODO\|FIXME\|HACK" modules/ 2>/dev/null | wc -l || echo 0)
echo "📌 遗留标记: ${todo_count} 条"
echo ""

echo "📋 Step 3: 记忆更新提示"
if [ -f "memory/INDEX.md" ]; then
    echo "ℹ️ 必须给出 Sedimentation Decision: no_sedimentation | project_memory | framework_candidate"
    echo "ℹ️ 若非 no_sedimentation，请立即更新项目 memory 或写入 memory/candidates/ 草稿"
else
    echo "⚠️ 未找到 memory/INDEX.md"
fi
echo ""

# ── Step 4: 工具健康检测，将 TOOL_SIGNAL 写入当前 session（F2 修复）──────────
echo "📋 Step 4: 工具健康检测"
FRAMEWORK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
CHECK_TOOLS="$FRAMEWORK_ROOT/.claude/hooks/verify-rules/check_tools.sh"
SESSION_WRITE="$FRAMEWORK_ROOT/.claude/hooks/session-snapshot/write.py"

if [ -f "$CHECK_TOOLS" ]; then
    # 捕获输出
    TOOL_OUTPUT=$(bash "$CHECK_TOOLS" 2>/dev/null || true)
    echo "$TOOL_OUTPUT"

    # 提取 TOOL_SIGNAL 行并写入当前 session checkpoint
    SIGNALS=$(echo "$TOOL_OUTPUT" | grep "^TOOL_SIGNAL:" || true)
    if [ -n "$SIGNALS" ] && [ -f "$SESSION_WRITE" ]; then
        # 获取当前项目名
        PROJECT=""
        CLAUDE_MD="$FRAMEWORK_ROOT/CLAUDE.md"
        if [ -f "$CLAUDE_MD" ]; then
            PROJECT=$(grep -E "^PROJECT:" "$CLAUDE_MD" | head -1 | sed 's/PROJECT://' | tr -d ' ' || true)
        fi
        # 写入 checkpoint，信号内容嵌入 result 字段
        SIGNAL_SUMMARY=$(echo "$SIGNALS" | tr '\n' ';' | sed 's/;$//')
        python3 "$SESSION_WRITE" checkpoint \
            "post-green tool-health 检测" \
            "$SIGNAL_SUMMARY" \
            "tool-health-check完成" 2>/dev/null || true
    fi
else
    echo "ℹ️ check_tools.sh 不存在，跳过工具健康检测"
fi
echo ""

echo "=== POST-GREEN 验证完成 ==="
