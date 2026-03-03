# SDD Framework v4

> Agent-Driven Project Reconstruction | SDD + TDD | Claude Code Native

## 快速开始
```bash
# 1. 放置参考项目
cp -r /your/reference /path/to/project/reference_project/

# 2. 激活环境
conda activate pcl-1.12

# 3. 启动 Claude Code（自动加载 CLAUDE.md）
claude

# 4. 分析参考项目
> @planner 分析 reference_project/ 并制定开发规划
```

## 结构
```
.claude/
  settings.json          ← Hooks（强制保障层）
  skills/                ← 5个 Skills（model-invoked）
    tdd-cycle/           ← TDD 开发循环
    spec-writer/         ← SPEC 编写
    validate-output/     ← 输出校验（context:fork）
    memory-update/       ← 经验沉淀
    diagnose-bug/        ← Bug 诊断（context:fork）
  agents/                ← 5个 Subagents
    planner.md           ← 规划（opus）
    implementer.md       ← 实现（sonnet）
    tester.md            ← 测试（sonnet）
    reviewer.md          ← 复审（sonnet，只读）
    diagnostician.md     ← 诊断（opus）
  hooks/                 ← 4个 Hook 脚本
CLAUDE.md                ← 项目上下文（自动加载）
memory/INDEX.md          ← 轻量记忆索引（必读入口）
modules/template/        ← 模块模板
projects/template_project/ ← 项目模板
tests/                   ← TDD 基础设施
```

## Hooks 保障
| Hook | 作用 |
|------|------|
| PreToolUse(Write/Edit) | 阻止写入 reference_project/（物理防护）|
| PreToolUse(Write) | 警告修改测试文件（要求说明原因）|
| PostToolUse(Bash) | 自动记录 pytest 结果到 tests/results_log.txt |
| Stop(prompt) | 会话结束前检查 TODO 和 Memory 是否已更新 |
