#!/usr/bin/env python3
"""
sdd-cli/versioning.py
SKILL/HOOK 文件版本语义管理工具（TASK-VER-01 ~ VER-04）

作为独立模块被 sdd-cli/cli.py 和 skill-tracker/tracker.py 引用，
也可直接运行：

用法:
  python3 .claude/tools/sdd-cli/versioning.py show <path>
  python3 .claude/tools/sdd-cli/versioning.py bump <path> minor   # 新增规则
  python3 .claude/tools/sdd-cli/versioning.py bump <path> patch   # 文字修正
  python3 .claude/tools/sdd-cli/versioning.py bump <path> major   # 语义变更
  python3 .claude/tools/sdd-cli/versioning.py archive <path>      # 归档当前版本
  python3 .claude/tools/sdd-cli/versioning.py init <path>         # 为文件添加 frontmatter

用途:
  管理 SKILL.md / HOOK.md 文件的语义化版本号，支持版本归档和历史回溯。

示例:
  python3 .claude/tools/sdd-cli/versioning.py show .claude/skills/tdd-cycle/SKILL.md
  python3 .claude/tools/sdd-cli/versioning.py bump .claude/skills/tdd-cycle/SKILL.md minor
  python3 .claude/tools/sdd-cli/versioning.py archive .claude/skills/tdd-cycle/SKILL.md
"""
import sys
import re
import argparse
from datetime import datetime
from pathlib import Path


def find_framework_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return Path.cwd()


ROOT = find_framework_root()
VERSIONS_DIR = ROOT / "memory" / "versions"

# 版本变更类型 → candidate_type 映射（供 tracker.py promote 调用）
CTYPE_TO_BUMP = {
    "skill_rule": "minor",       # 新增规则 = MINOR
    "hook_trigger": "minor",
    "hook_check": "minor",
    "agent_constraint": "minor",
    "agent_role_gap": "major",   # 新增 Agent = MAJOR
    "tool_subcommand": "minor",
    "tool_new": "major",
    "permission_relax": "patch",
    "permission_tighten": "minor",
    "test_stub": "patch",
    "command_missing": "minor",
    "planner_risk_dimension_missing": "minor",
}


def read_frontmatter(content: str) -> tuple[dict, str]:
    """
    解析文件内容，返回 (frontmatter_dict, body_without_frontmatter)。
    frontmatter 格式：第一行 ---，结束行 ---（YAML 子集）。
    """
    fm = {}
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return fm, content

    end_idx = -1
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx == -1:
        return fm, content

    for line in lines[1:end_idx]:
        m = re.match(r"^([\w_-]+):\s*(.*)$", line.strip())
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"\'')

    body = "\n".join(lines[end_idx + 1:])
    return fm, body


def write_frontmatter(fm: dict, body: str) -> str:
    """将 frontmatter dict 和 body 组合为完整文件内容。"""
    fm_lines = ["---"]
    # 固定字段顺序
    key_order = ["id", "version", "recommended", "changelog", "last_updated"]
    for key in key_order:
        if key in fm:
            fm_lines.append(f"{key}: {fm[key]}")
    for key, val in fm.items():
        if key not in key_order:
            fm_lines.append(f"{key}: {val}")
    fm_lines.append("---")
    return "\n".join(fm_lines) + "\n" + body.lstrip("\n")


def parse_version(version_str: str) -> tuple[int, int, int]:
    """解析 '1.2.3' → (1, 2, 3)，解析失败返回 (1, 0, 0)。"""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str.strip())
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return 1, 0, 0


def bump_version(version_str: str, bump_type: str) -> str:
    """
    根据 bump_type（major/minor/patch）递增版本号。
    - patch：文字修正，不影响行为
    - minor：新增规则/检查项，向后兼容
    - major：规则语义变更，可能影响现有项目
    """
    major, minor, patch = parse_version(version_str)
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def get_skill_id(fpath: Path) -> str:
    """从文件路径推导 skill id：通常是父目录名。"""
    content = fpath.read_text(encoding="utf-8")
    fm, _ = read_frontmatter(content)
    if fm.get("id"):
        return fm["id"]
    return fpath.parent.name


def cmd_show(args):
    """显示文件当前版本信息。"""
    fpath = Path(args.path)
    if not fpath.exists():
        print(f"❌ 文件不存在: {fpath}")
        sys.exit(1)
    content = fpath.read_text(encoding="utf-8")
    fm, _ = read_frontmatter(content)
    if not fm:
        print(f"ℹ️  {fpath.name} 尚无 frontmatter（运行 init 添加）")
        return
    print(f"📄 {fpath.name}")
    print(f"  id:           {fm.get('id', '（未设置）')}")
    print(f"  version:      {fm.get('version', '（未设置）')}")
    print(f"  recommended:  {fm.get('recommended', 'true')}")
    print(f"  last_updated: {fm.get('last_updated', '（未设置）')}")

    # 查找历史版本
    skill_id = fm.get("id") or fpath.parent.name
    ver_dir = VERSIONS_DIR / skill_id
    if ver_dir.exists():
        versions = sorted(ver_dir.glob("*.md"))
        if versions:
            print(f"  归档版本: {', '.join(v.stem for v in versions)}")


def cmd_init(args):
    """为文件添加标准 frontmatter（若已有则跳过）。"""
    fpath = Path(args.path)
    if not fpath.exists():
        print(f"❌ 文件不存在: {fpath}")
        sys.exit(1)
    content = fpath.read_text(encoding="utf-8")
    fm, body = read_frontmatter(content)

    if fm.get("version"):
        print(f"ℹ️  {fpath.name} 已有 frontmatter（version: {fm['version']}），跳过")
        return

    # 推导 id
    skill_id = fpath.parent.name
    # 尝试从第一个 # 标题提取
    for line in content.splitlines():
        if line.startswith("# "):
            title_part = re.sub(r"^(SKILL:|HOOK:|Agent:)\s*", "", line[2:]).strip()
            if title_part:
                skill_id = fpath.parent.name  # 保持目录名作为 id
            break

    fm = {
        "id": skill_id,
        "version": "1.0.0",
        "recommended": "true",
        "changelog": "memory/skill-changelog.md",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
    }
    new_content = write_frontmatter(fm, body if fm else content)
    fpath.write_text(new_content, encoding="utf-8")
    print(f"✅ {fpath.name} 已添加 frontmatter（version: 1.0.0）")


def cmd_bump(args):
    """
    递增版本号并归档旧版本（TASK-VER-02）。
    bump_type: major / minor / patch
    """
    fpath = Path(args.path)
    if not fpath.exists():
        print(f"❌ 文件不存在: {fpath}")
        sys.exit(1)

    content = fpath.read_text(encoding="utf-8")
    fm, body = read_frontmatter(content)

    if not fm.get("version"):
        # 先 init
        cmd_init(argparse.Namespace(path=args.path))
        content = fpath.read_text(encoding="utf-8")
        fm, body = read_frontmatter(content)

    old_version = fm.get("version", "1.0.0")
    new_version = bump_version(old_version, args.bump_type)

    # 先归档旧版本（TASK-VER-04）
    _archive_version(fpath, fm, body, old_version)

    # 写入新版本
    fm["version"] = new_version
    fm["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    new_content = write_frontmatter(fm, body)
    fpath.write_text(new_content, encoding="utf-8")

    print(f"✅ {fpath.name}: {old_version} → {new_version} ({args.bump_type})")
    print(f"   旧版本已归档到 memory/versions/{fm.get('id', fpath.parent.name)}/{old_version}.md")


def _archive_version(fpath: Path, fm: dict, body: str, version: str):
    """将当前版本归档到 memory/versions/<id>/<version>.md（TASK-VER-04）。"""
    skill_id = fm.get("id") or fpath.parent.name
    ver_dir = VERSIONS_DIR / skill_id
    ver_dir.mkdir(parents=True, exist_ok=True)
    archive_path = ver_dir / f"{version}.md"
    if not archive_path.exists():
        archive_content = write_frontmatter(fm, body)
        archive_path.write_text(archive_content, encoding="utf-8")


def cmd_archive(args):
    """手动归档当前版本（不递增版本号）。"""
    fpath = Path(args.path)
    if not fpath.exists():
        print(f"❌ 文件不存在: {fpath}")
        sys.exit(1)
    content = fpath.read_text(encoding="utf-8")
    fm, body = read_frontmatter(content)
    if not fm.get("version"):
        print(f"⚠️  {fpath.name} 无版本号，请先运行 init")
        sys.exit(1)
    _archive_version(fpath, fm, body, fm["version"])
    skill_id = fm.get("id") or fpath.parent.name
    print(f"✅ 已归档 {fpath.name} v{fm['version']} → memory/versions/{skill_id}/{fm['version']}.md")


def bump_on_promote(target_file: str, candidate_type: str) -> str:
    """
    供 skill-tracker/tracker.py promote 调用。
    根据 candidate_type 推断版本变更类型，执行 bump，返回新版本号。
    若目标文件无 frontmatter，先 init 再 bump。
    """
    fpath = ROOT / target_file
    if not fpath.exists():
        return ""

    bump_type = CTYPE_TO_BUMP.get(candidate_type, "patch")
    content = fpath.read_text(encoding="utf-8")
    fm, body = read_frontmatter(content)

    if not fm.get("version"):
        # 初始化 frontmatter
        skill_id = fpath.parent.name
        fm = {
            "id": skill_id,
            "version": "1.0.0",
            "recommended": "true",
            "changelog": "memory/skill-changelog.md",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
        }
        # 首次 init 不需要归档
    else:
        old_version = fm["version"]
        _archive_version(fpath, fm, body, old_version)

    new_version = bump_version(fm.get("version", "1.0.0"), bump_type)
    fm["version"] = new_version
    fm["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    new_content = write_frontmatter(fm, body)
    fpath.write_text(new_content, encoding="utf-8")
    return new_version


def main():
    parser = argparse.ArgumentParser(
        description="SKILL/HOOK 文件版本语义管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  为 SKILL.md / HOOK.md 文件管理语义化版本号（MAJOR.MINOR.PATCH）。
  promote 时自动调用 bump，归档旧版本到 memory/versions/。

示例:
  python3 versioning.py show .claude/skills/tdd-cycle/SKILL.md
  python3 versioning.py init .claude/skills/tdd-cycle/SKILL.md
  python3 versioning.py bump .claude/skills/tdd-cycle/SKILL.md minor
  python3 versioning.py archive .claude/skills/tdd-cycle/SKILL.md
""",
    )
    subparsers = parser.add_subparsers(dest="cmd")

    sp = subparsers.add_parser("show", help="显示文件版本信息")
    sp.add_argument("path", help="SKILL.md / HOOK.md 路径")

    sp = subparsers.add_parser("init", help="为文件添加标准 frontmatter（首次使用）")
    sp.add_argument("path", help="SKILL.md / HOOK.md 路径")

    sp = subparsers.add_parser("bump", help="递增版本号并归档旧版本")
    sp.add_argument("path", help="SKILL.md / HOOK.md 路径")
    sp.add_argument("bump_type", choices=["major", "minor", "patch"],
                    help="版本变更类型：major（语义变更）/ minor（新增规则）/ patch（文字修正）")

    sp = subparsers.add_parser("archive", help="手动归档当前版本（不递增）")
    sp.add_argument("path", help="SKILL.md / HOOK.md 路径")

    args = parser.parse_args()
    dispatch = {"show": cmd_show, "init": cmd_init, "bump": cmd_bump, "archive": cmd_archive}

    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
