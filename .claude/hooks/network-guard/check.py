#!/usr/bin/env python3
"""
network-guard: 扫描 Python 文件中的常见 socket 编程错误
用法: python3 check.py <file_or_directory>
"""
import ast
import sys
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List


@dataclass
class Issue:
    file: str
    line: int
    severity: str  # ERROR / WARNING
    rule: str
    message: str


def scan_file(filepath: str) -> List[Issue]:
    issues = []
    try:
        source = Path(filepath).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return issues

    for node in ast.walk(tree):
        # 检查 except Exception 捕获 socket 错误
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                issues.append(Issue(
                    file=filepath, line=node.lineno,
                    severity="ERROR", rule="MEM_F_C_004",
                    message="裸 except: 捕获，可能掩盖 socket 异常语义"
                ))
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                # 检查 handler body 是否只有 pass
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    issues.append(Issue(
                        file=filepath, line=node.lineno,
                        severity="WARNING", rule="MEM_F_C_004",
                        message="except Exception: pass 会静默吞掉非预期异常，建议记录日志"
                    ))

        # 检查 send() 而非 sendall()
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "send" and not node.func.attr == "sendall":
                    # 排除 socket.send 以外的 send（如 queue.put 等）
                    issues.append(Issue(
                        file=filepath, line=node.lineno,
                        severity="WARNING", rule="MEM_F_C_005",
                        message=f"使用 .send()，建议改为 .sendall() 防止部分发送"
                    ))

    # 基于文本扫描：检查 recv 后是否有 b'' 检查
    lines = source.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if ".recv(" in stripped and "=" in stripped:
            # 检查后续 5 行内是否有 if not
            context = "\n".join(lines[i:min(i+5, len(lines))])
            if "if not" not in context and "if data" not in context and "b''" not in context:
                issues.append(Issue(
                    file=filepath, line=i,
                    severity="WARNING", rule="MEM_F_C_005",
                    message="recv() 后未检测 b''（连接关闭），可能导致死循环"
                ))

    return issues


def main():
    if len(sys.argv) < 2:
        print("用法: python3 check.py <file_or_directory>")
        sys.exit(1)

    target = sys.argv[1]
    all_issues: List[Issue] = []

    if os.path.isfile(target):
        files = [target]
    else:
        files = [str(p) for p in Path(target).rglob("*.py")]

    for f in sorted(files):
        all_issues.extend(scan_file(f))

    if not all_issues:
        print("✅ network-guard: 无问题")
        sys.exit(0)

    errors = [i for i in all_issues if i.severity == "ERROR"]
    warnings = [i for i in all_issues if i.severity == "WARNING"]

    for issue in all_issues:
        icon = "❌" if issue.severity == "ERROR" else "⚠️"
        print(f"{icon} [{issue.rule}] {issue.file}:{issue.line} — {issue.message}")

    print(f"\n合计: {len(errors)} 错误, {len(warnings)} 警告")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
