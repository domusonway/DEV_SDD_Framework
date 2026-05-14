#!/usr/bin/env python3
"""
Layer 2: 模型触发测试
验证：给定特定场景，模型是否能识别并选择正确的 Skill/Hook

测试逻辑：
  1. 注入 CLAUDE.md 的"按需加载地图"作为 system prompt
  2. 给模型一个场景描述
  3. 让模型回答"你应该读取哪个文件，为什么"
  4. 用 judge() 语义判断答案是否正确

这验证了 Skill 的"激活条件"描述是否清晰，以及模型是否能正确匹配。
"""
import sys
from pathlib import Path

# 添加父目录到 path
sys.path.insert(0, str(Path(__file__).parent))
from _api_client import read_skill, call_model, assert_model, AssertionError as ModelAssertionError

FRAMEWORK_ROOT = Path(__file__).parent.parent.parent.parent

# 从 CLAUDE.md 提取"按需加载地图"作为 system context
ROUTING_SYSTEM = """
你是一个遵循 DEV SDD 框架的 AI 编程助手。

框架的"按需加载地图"如下（这决定了你在不同场景下应该读取哪个文件）：

| 当前任务 | 读取路径 |
|---------|---------|
| 任何任务开始 | memory/INDEX.md |
| 收到开发任务 | .claude/skills/complexity-assess/SKILL.md |
| TDD 实现阶段 | .claude/skills/tdd-cycle/SKILL.md |
| 出现 Bug / RED > 2次 | .claude/skills/diagnose-bug/SKILL.md |
| 所有测试 GREEN 后 | .claude/skills/validate-output/SKILL.md |
| 项目完成后 | .claude/skills/memory-update/SKILL.md |
| 涉及 HTTP 协议 | memory/domains/http/INDEX.md |
| H 模式多模块规划 | .claude/agents/planner.md |
| 长任务/复杂任务/交付结论前 | .claude/hooks/challenge-gate/HOOK.md + .claude/agents/challenger.md |
| 写任何网络代码后 | .claude/hooks/network-guard/HOOK.md（立即执行）|
| RED 超过 2 次 | .claude/hooks/stuck-detector/HOOK.md（立即执行）|
| 所有测试 GREEN | .claude/hooks/post-green/HOOK.md（立即执行）|

当我描述一个场景，请告诉我：
1. 你应该读取哪个文件（精确路径）
2. 为什么（对应加载地图的哪一行）
""".strip()


TRIGGER_CASES = [
    {
        "name": "新开发任务触发 complexity-assess",
        "scenario": "用户给我一个任务：实现一个支持并发的 TCP 聊天服务器，包含消息广播和私聊功能。这是我收到的第一个任务指令。",
        "criterion": "模型应该指出需要读取 .claude/skills/complexity-assess/SKILL.md，因为收到开发任务时第一步是评估复杂度",
        "expected_path": "complexity-assess",
    },
    {
        "name": "RED 超过 2 次触发 stuck-detector",
        "scenario": "我正在实现 parse_request 模块。测试连续失败了 3 次：第一次我改了正则表达式，第二次我改了 bytes 解码方式，第三次改了异常捕获，但测试还是 RED。",
        "criterion": "模型应该指出需要立即读取并执行 .claude/hooks/stuck-detector/HOOK.md，因为 RED 状态超过 2 次",
        "expected_path": "stuck-detector",
    },
    {
        "name": "所有测试变绿触发 post-green",
        "scenario": "刚才运行 pytest，结果是 8/8 PASS，所有测试全部通过了，包括 request_parser、response、router 三个模块。",
        "criterion": "模型应该指出需要立即执行 .claude/hooks/post-green/HOOK.md，因为所有测试变为 GREEN",
        "expected_path": "post-green",
    },
    {
        "name": "写 socket 代码后触发 network-guard",
        "scenario": "我刚写完 server.py，里面包含 conn.recv(4096) 和 conn.sendall(response) 的代码，准备运行测试。",
        "criterion": "模型应该指出需要立即读取并执行 .claude/hooks/network-guard/HOOK.md，因为写了含 recv/send/socket 的代码",
        "expected_path": "network-guard",
    },
    {
        "name": "HTTP 相关任务加载领域记忆",
        "scenario": "我需要实现 HTTP 响应构建模块，要返回正确格式的 HTTP/1.0 响应，包括状态行、响应头和响应体。",
        "criterion": "模型应该指出需要读取 memory/domains/http/INDEX.md，因为任务涉及 HTTP 协议实现",
        "expected_path": "domains/http",
    },
    {
        "name": "项目完成后触发 memory-update",
        "scenario": "所有模块实现完毕，validate-output 验收也通过了，整个项目准备交付。",
        "criterion": "模型应该指出需要执行 .claude/skills/memory-update/SKILL.md，因为项目完成后需要沉淀记忆",
        "expected_path": "memory-update",
    },
    {
        "name": "高复杂度触发 H 模式 Planner",
        "scenario": "复杂度评估结果：模块数=4, 外部依赖=1, 并发=2, 状态=1, 测试=2, 总分=10。进入 H 模式，需要开始规划。",
        "criterion": "模型应该指出需要读取 .claude/agents/planner.md，因为是 H 模式需要依赖拓扑分析",
        "expected_path": "planner",
    },
    {
        "name": "交付结论前触发 challenge-gate",
        "scenario": "这是一个长任务，刚完成所有验证，准备输出最终结论并声明交付就绪。",
        "criterion": "模型应该指出需要读取 .claude/hooks/challenge-gate/HOOK.md，并在命中时读取 .claude/agents/challenger.md，因为长任务或交付结论前需要质疑复核",
        "expected_path": "challenge-gate",
    },
]


def run_test(case: dict) -> tuple[bool, str]:
    try:
        response = call_model(
            user_message=f"场景描述：{case['scenario']}",
            system=ROUTING_SYSTEM,
            max_tokens=400,
        )
        assert_model(response, case["criterion"], context=case["scenario"])
        return True, ""
    except ModelAssertionError as e:
        return False, str(e)
    except Exception as e:
        return False, f"API 错误: {e}"


def main():
    print("Layer 2 · 模型触发测试")
    print(f"{'─'*50}")
    failed = 0
    for case in TRIGGER_CASES:
        passed, reason = run_test(case)
        icon = "✅" if passed else "❌"
        print(f"  {icon} {case['name']}")
        if not passed:
            for line in reason.strip().splitlines()[:4]:
                print(f"      {line}")
            failed += 1
    print(f"{'─'*50}")
    print(f"  {len(TRIGGER_CASES) - failed}/{len(TRIGGER_CASES)} 通过")
    sys.exit(failed)


if __name__ == "__main__":
    main()
