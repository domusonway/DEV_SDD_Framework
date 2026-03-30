#!/usr/bin/env python3
"""
test-sync/sync.py
比对 SKILL.md 规则与 skill-tests/cases/ 的测试覆盖，追加缺失测试桩

用法:
  python3 .claude/hooks/test-sync/sync.py --skill tdd-cycle
  python3 .claude/hooks/test-sync/sync.py --all
"""
import re
import ast
import sys
import argparse
from datetime import datetime
from pathlib import Path


def find_framework_root() -> Path:
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return current


ROOT = find_framework_root()
SKILLS_DIR = ROOT / ".claude" / "skills"
HOOKS_DIR = ROOT / ".claude" / "hooks"
TESTS_DIR = ROOT / "skill-tests" / "cases"
CHANGELOG = ROOT / "memory" / "skill-changelog.md"

# SKILL id → 测试文件名映射
SKILL_TO_TEST = {
    "tdd-cycle": "test_tdd_cycle.py",
    "complexity-assess": "test_complexity_assess.py",
    "diagnose-bug": "test_diagnose_bug.py",
    "memory-update": "test_memory_update.py",
    "validate-output": "test_validate_output.py",
    "observe-verify": "test_observe_verify.py",
    "sub-agent-isolation": "test_sub_agent_isolation.py",
    "context-probe": None,  # context-probe 无独立测试文件，跳过
    "network-guard": "test_hook_network_guard.py",
    "post-green": "test_hook_post_green.py",
    "stuck-detector": "test_hook_stuck_detector.py",
    "context-budget": "test_context_budget.py",
    "meta-skill-agent": "test_meta_skill_loop.py",
    # M1修复：补充新增 hook 的测试映射
    "hook-observer": "test_meta_skill_loop.py",
    "permission-auditor": "test_meta_skill_loop.py",
    "test-sync": "test_meta_skill_loop.py",
}


def extract_rules_from_skill(skill_path: Path) -> list[dict]:
    """
    从 SKILL.md 提取可测试的规则条目。
    提取来源：
    - "禁止行为" / "禁止" 章节下的列表项
    - "必须" 开头的列表项
    - "不可" 开头的列表项
    """
    content = skill_path.read_text(encoding="utf-8")
    rules = []

    # 提取禁止行为章节
    forbidden_section = re.search(
        r"## 禁止行为\s*(.*?)(?=\n## |\Z)", content, re.DOTALL
    )
    if forbidden_section:
        for line in forbidden_section.group(1).splitlines():
            line = line.strip().lstrip("- ")
            if line and len(line) > 5:
                rules.append({
                    "text": line,
                    "key_phrase": _extract_key_phrase(line),
                    "slug": _to_slug(line),
                    "source": "forbidden_section",
                })

    # 提取"必须"开头的条目
    for line in content.splitlines():
        stripped = line.strip().lstrip("- []x~ ")
        if stripped.startswith("必须") or stripped.startswith("不可") or stripped.startswith("禁止"):
            if len(stripped) > 8 and stripped not in [r["text"] for r in rules]:
                rules.append({
                    "text": stripped,
                    "key_phrase": _extract_key_phrase(stripped),
                    "slug": _to_slug(stripped),
                    "source": "inline",
                })

    return rules[:20]  # 最多 20 条，防止过多桩函数


def _extract_key_phrase(text: str) -> str:
    """提取规则的核心短语用于断言"""
    # 提取引号内的内容
    quoted = re.findall(r'[`"「」『』]([^`"「」『』]{3,30})[`"「」『』]', text)
    if quoted:
        return quoted[0]
    # 取前 15 个字符作为关键短语
    return text[:15].strip()


def _to_slug(text: str) -> str:
    """将规则文本转为合法的 Python 函数名片段"""
    # 保留英文字母数字，中文转拼音首字母（简化处理：直接截取前 6 字符的 ord 特征）
    clean = re.sub(r"[^\w\u4e00-\u9fff]", "_", text)
    clean = re.sub(r"_+", "_", clean)[:30].strip("_")
    return clean.lower()


def get_covered_rules(test_path: Path) -> set[str]:
    """解析测试文件，返回已有测试函数的名称集合"""
    if not test_path.exists():
        return set()
    try:
        tree = ast.parse(test_path.read_text(encoding="utf-8"))
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        }
    except SyntaxError:
        return set()


def generate_stub(rule: dict, skill_path: Path) -> str:
    """生成 Layer 1 结构测试桩"""
    slug = rule["slug"]
    text_preview = rule["text"][:40]
    key_phrase = rule["key_phrase"]

    return f'''
def test_{slug}_rule_exists():
    """AUTO-SYNCED {datetime.now().strftime('%Y-%m-%d')}: 覆盖规则 '{text_preview}...'"""
    content = SKILL_PATH.read_text()
    assert "{key_phrase}" in content, (
        "规则 '{text_preview}' 已从 SKILL.md 中删除或修改，"
        "请同步更新此测试"
    )
'''


def sync_skill(skill_id: str) -> tuple[int, list[str]]:
    """同步单个 skill 的测试覆盖，返回 (新增数量, 新增函数名列表)"""
    test_filename = SKILL_TO_TEST.get(skill_id)
    if not test_filename:
        print(f"  ⏭  {skill_id}: 无对应测试文件，跳过")
        return 0, []

    # 找 SKILL.md
    skill_path = SKILLS_DIR / skill_id / "SKILL.md"
    if not skill_path.exists():
        # 也可能是 hook
        hook_path = HOOKS_DIR / skill_id / "HOOK.md"
        if hook_path.exists():
            skill_path = hook_path
        else:
            print(f"  ❌ {skill_id}: SKILL.md 不存在，跳过")
            return 0, []

    test_path = TESTS_DIR / test_filename
    rules = extract_rules_from_skill(skill_path)
    covered = get_covered_rules(test_path)

    # 找未覆盖的规则（按 slug 匹配）
    uncovered = [
        r for r in rules
        if f"test_{r['slug']}_rule_exists" not in covered
    ]

    if not uncovered:
        print(f"  ✅ {skill_id}: 测试覆盖完整（{len(rules)} 条规则）")
        return 0, []

    # 追加桩到测试文件
    stubs = [generate_stub(r, skill_path) for r in uncovered]

    if test_path.exists():
        existing = test_path.read_text(encoding="utf-8")
        # 确保 SKILL_PATH 变量存在
        if "SKILL_PATH" not in existing:
            # 在文件顶部插入（简化：追加到文件开头的 import 区域之后）
            pass
        new_content = existing.rstrip() + "\n\n# AUTO-SYNCED by test-sync\n" + "".join(stubs)
    else:
        # 创建新测试文件
        new_content = f'''#!/usr/bin/env python3
"""AUTO-GENERATED by test-sync — {skill_id} 测试"""
from pathlib import Path
import sys

SKILL_PATH = Path(__file__).parent.parent.parent / "{skill_path.relative_to(ROOT)}"


def test_skill_exists():
    assert SKILL_PATH.exists(), f"SKILL.md 不存在: {{SKILL_PATH}}"

{"".join(stubs)}

if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t(); print(f"  ✅ {{t.__name__}}")
        except AssertionError as e:
            print(f"  ❌ {{t.__name__}}: {{e}}"); failed += 1
    sys.exit(failed)
'''

    test_path.write_text(new_content, encoding="utf-8")
    new_names = [f"test_{r['slug']}_rule_exists" for r in uncovered]
    print(f"  ✅ {skill_id}: 追加 {len(uncovered)} 个测试桩 → {test_filename}")
    for name in new_names[:3]:
        print(f"     + {name}")
    if len(new_names) > 3:
        print(f"     ... 及 {len(new_names) - 3} 个更多")

    return len(uncovered), new_names


def update_changelog(skill_id: str, new_names: list[str]):
    """在 skill-changelog.md 中记录测试同步事件"""
    if not CHANGELOG.exists():
        return
    entry = f"""
### 测试同步 — {skill_id} — {datetime.now().strftime('%Y-%m-%d')}
- 由 test-sync hook 自动追加 {len(new_names)} 个测试桩
- 新增函数：{', '.join(new_names[:5])}{'...' if len(new_names) > 5 else ''}
"""
    existing = CHANGELOG.read_text(encoding="utf-8")
    CHANGELOG.write_text(existing + entry, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Test-Sync — 同步 SKILL 规则到测试覆盖")
    parser.add_argument("--skill", help="指定 skill id")
    parser.add_argument("--all", action="store_true", help="同步全部 skills")
    args = parser.parse_args()

    skills_to_sync = []
    if args.all:
        skills_to_sync = list(SKILL_TO_TEST.keys())
    elif args.skill:
        skills_to_sync = [args.skill]
    else:
        print("请指定 --skill <id> 或 --all")
        sys.exit(1)

    print(f"\n[test-sync] 开始同步 {len(skills_to_sync)} 个 skill 的测试覆盖")
    total_new = 0
    for skill_id in skills_to_sync:
        count, names = sync_skill(skill_id)
        total_new += count
        if names:
            update_changelog(skill_id, names)

    print(f"\n[test-sync] 完成，共追加 {total_new} 个测试桩")
    if total_new > 0:
        print("  运行 Layer 1 验证：python3 skill-tests/run_all.py")


if __name__ == "__main__":
    main()
