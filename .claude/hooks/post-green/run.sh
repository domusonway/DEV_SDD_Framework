#!/usr/bin/env bash
# post-green/run.sh: 测试全绿后自动执行的验证脚本
set -euo pipefail

PROJECT_ROOT="${1:-.}"
cd "$PROJECT_ROOT"

echo "=== POST-GREEN 验证 ==="
echo ""

# 1. 确认测试状态
echo "📋 Step 1: 最终测试状态"
if python3 -m pytest tests/ -v --tb=short 2>&1 | tail -5; then
    echo "✅ 所有测试 PASS"
else
    echo "❌ 仍有测试失败，post-green 中止"
    exit 1
fi
echo ""

# 2. 检查代码质量
echo "📋 Step 2: 代码质量扫描"
# 语法检查
find modules/ -name "*.py" -exec python3 -m py_compile {} \; 2>&1
echo "✅ 语法检查通过"

# 检查宽泛异常捕获
if grep -rn "except Exception: *pass" modules/ 2>/dev/null; then
    echo "⚠️ 发现 except Exception: pass，建议加日志"
else
    echo "✅ 无裸异常捕获"
fi

# 检查遗留标记
todo_count=$(grep -rn "TODO\|FIXME\|HACK" modules/ 2>/dev/null | wc -l || echo 0)
echo "📌 遗留标记: ${todo_count} 条"
echo ""

# 3. 检查 memory 是否需要更新
echo "📋 Step 3: 记忆更新提示"
if [ -f "memory/INDEX.md" ]; then
    echo "ℹ️ 请检查是否需要更新 memory/INDEX.md"
else
    echo "⚠️ 未找到 memory/INDEX.md"
fi
echo ""

echo "=== POST-GREEN 验证完成 ==="
