# DEV SDD Framework

> **规格驱动开发 (Spec-Driven Development) 框架** — 让 AI 编程 Agent 在长周期项目中始终保持精准、可追踪、自进化

[![Framework Version](https://img.shields.io/badge/version-v3.1-blue)](CLAUDE.md)
[![License](https://img.shields.io/badge/license-MIT-green)](#)

---

## 什么是 DEV SDD Framework？

大多数 AI 编程工作流在短任务上表现优秀，但面对多模块、多会话的长时开发任务时会暴露两个根本问题：

- **知识遗忘**：每次新对话，Agent 对项目约束、踩坑经验、设计决策一无所知
- **过程失控**：没有强制流程，Agent 跳过测试、绕过检查、硬编码骗过断言

DEV SDD Framework 是一套跑在 Claude Code（或任何支持 CLAUDE.md 的编码 Agent）上的**元框架**，通过三个机制解决这两个问题：

1. **规格优先**：每个模块有 SPEC.md，所有实现以规格为契约，测试是规格的唯一表达
2. **分层记忆**：会话快照 → 项目经验 → 跨项目框架规则，形成持久化知识库
3. **Meta-Skill Loop**：框架自省，从执行历史中发现改进候选，经人工审核后升级规则

---

## 快速上手

### 前提

- Claude Code（推荐）或其他支持工具调用的编码 Agent
- Python 3.10+
- Git

### 安装

```bash
git clone https://github.com/your-org/dev-sdd-framework.git
cd dev-sdd-framework

# 给脚本添加执行权限
chmod +x .claude/hooks/verify-rules/check.sh
chmod +x .claude/hooks/session-snapshot/write.py

# 创建新项目
# /project:new my-project
```

### 在 Claude.ai 配置 Project Rules

将 `docs/PROJECT_RULES.md` 中"Rules 正文"部分粘贴到你的 Claude.ai 项目设置 → Project Instructions。这是让 Agent 在每次对话开始时自动续接进度的关键。

### 验证安装

```bash
bash .claude/hooks/verify-rules/check.sh
```

---

## 框架结构

```
dev-sdd-framework/
│
├── CLAUDE.md                     # 框架主入口，Agent 启动协议
├── .claude/
│   ├── skills/                   # 可复用技能（TDD 循环、Bug 诊断等）
│   ├── hooks/                    # 自动触发检查（网络安全、会话快照等）
│   ├── agents/                   # H 模式 Agent 分工定义
│   ├── commands/                 # 快捷命令（/project:new、/project:switch 等）
│   ├── tools/                    # 追踪工具（计划追踪、技能追踪）
│   └── settings.local.json       # Claude Code 权限配置
│
├── memory/                       # 框架级跨项目记忆库
│   ├── INDEX.md                  # CRITICAL + IMPORTANT 规则索引
│   ├── critical/                 # 高置信度规则（≥3 个项目验证）
│   ├── important/                # 领域规则
│   ├── domains/                  # 按技术域分类记忆（HTTP、TDD、并发等）
│   ├── candidates/               # Meta-Skill Loop 候选池
│   └── skill-changelog.md        # 规则变更历史
│
├── projects/                     # 各项目独立目录（不纳入框架 git）
│   └── _template/                # 新项目模板
│
└── skill-tests/                  # 框架自身的三层验证测试
    ├── cases/                    # Layer 1：文档结构测试（无 API）
    ├── model/                    # Layer 2/3：模型触发与行为测试
    └── generated/                # 自动生成的测试用例
```

---

## 核心概念

### 三种工作模式

复杂度评估完成后，框架自动分流到对应模式：

| 模式 | 评分 | 适用场景 | 文档要求 |
|------|------|---------|---------|
| **L 轻量** | 0–3 | 单模块、无并发 | BRIEF.md（≤15行）|
| **M 标准** | 4–7 | 多模块、有依赖 | CONTEXT.md + 各模块 SPEC.md |
| **H 完整** | 8+ | 复杂系统、长时任务 | 完整文档套件 + Agent 流水线 |

### TDD 循环

每个模块必须完整经历 **RED → GREEN → REFACTOR → VALIDATE → UPDATE-PLAN** 五个阶段。强制约束包括：

- RED 阶段必须确认测试 FAIL，不 FAIL = 测试写错
- GREEN 阶段禁止修改断言或用硬编码骗过测试
- 连续 RED 超过 2 次，自动触发 `stuck-detector`

### 记忆分层

```
会话快照 (session snapshots)
    ↓ post-green 后判断
项目记忆 (projects/<name>/memory/)
    ↓ ≥3 个项目验证
框架记忆 (memory/INDEX.md)
    ↑↑↑
Meta-Skill Loop 候选 (memory/candidates/)
```

### Meta-Skill Loop（v3.1 新增）

框架自进化机制。六类观察器从执行历史中发现改进点，写入候选池，经人工审核后升级到框架规则：

| 观察器 | 发现什么 |
|--------|---------|
| `meta-skill-agent` | SKILL 规则缺失或不完整 |
| `hook-observer` | Hook 触发条件漏洞（如 asyncio 未覆盖）|
| `agent-auditor` | Agent 协作链路缺陷 |
| `check_tools.sh` | 工具功能缺失信号 |
| `permission-auditor` | 权限边界过宽或过窄 |
| `test-sync` | 规则变更后测试覆盖缺口 |

所有候选只写入 `memory/candidates/`，**不自动修改任何框架文件**。通过 `/project:skill-review` 人工审核后执行提升。

---

## 常用命令

```bash
# 项目管理
/project:new <name>           # 从模板创建新项目
/project:switch <name>        # 切换激活项目
/project:validate             # 运行框架技能验证测试

# 记忆与候选审核
/project:memory-update        # 手动触发记忆沉淀
/project:skill-review         # 审核并提升 Meta-Skill Loop 候选

# 工具脚本
python3 .claude/tools/plan-tracker/tracker.py status     # 查看项目进度
python3 .claude/tools/skill-tracker/tracker.py candidates  # 查看待审核候选
bash .claude/hooks/verify-rules/check.sh                 # 每日健康检查
```

---

## Hook 触发规则

以下 Hook 由框架自动触发，**不可跳过**：

| 触发时机 | Hook | 原因 |
|---------|------|------|
| 写了含 recv/send/socket 的代码后 | `network-guard` | TCP 编程有隐性 Bug，E2E 才爆 |
| 同一测试连续 RED > 2 次 | `stuck-detector` | 防止在错误方向无限循环 |
| 所有测试变 GREEN | `post-green` | 触发验收 + 记忆沉淀判断 |
| 任意决策完成 / 对话结束前 | `session-snapshot` | 过程记录，支持跨会话续接 |
| 项目交付后 | `hook-observer` + `permission-auditor` | 检测框架健康度 |
| `/project:skill-review` promote 后 | `test-sync` | 确保新规则有测试覆盖 |

---

## 测试体系

框架自身有三层测试，验证规则文档和模型行为是否一致：

```bash
# Layer 1：文档结构（无 API 调用，CI 默认）
python3 skill-tests/run_all.py

# Layer 2：模型触发（验证 Agent 是否选对了 Skill）
python3 skill-tests/run_all.py --layer 2

# Layer 3：模型行为（验证 Agent 是否真正遵守约束）
python3 skill-tests/run_all.py --layer 3

# 先更新用例再测试
python3 skill-tests/run_all.py --layer 3 --regenerate
```

---

## 项目示例

`projects/sdd-tinyhttpd/` 是框架附带的参考项目，用 Python 重实现 tinyhttpd（一个极简 HTTP/1.0 服务器）。它完整演示了：

- H 模式六模块分批次实现（request_parser → response → router → static_handler → cgi_handler → server）
- 网络代码 Bug 经验沉淀（P_THD_001：str 误当 bytes，P_THD_002：recv b'' 未检查）
- 框架 CRITICAL 规则的触发场景（MEM_F_C_004、MEM_F_C_005）

---

## 设计哲学

**规格是代码的唯一真相**。测试断言是规格的可执行表达，禁止通过修改断言来让测试通过。

**记忆要精简，不要堆积**。记忆的价值在于"下次遇到 X 场景时做 Y"，而不是"我学到了 Z"。CRITICAL 区上限 7 条，超出必须合并。

**框架改进需要人工确认**。观察器只写候选，不自动修改规则。这是安全边界，也是人类保持对框架演化控制权的机制。

**宁可多交接，不要 context rot**。Context 质量随长度下降。H 模式每个批次结束时强制检查 budget，危险时立即执行 Session 交接并写 HANDOFF.json。

---

## 贡献

框架规则通过 Meta-Skill Loop 演化。如果你在使用过程中发现了系统性问题：

1. 运行 `/project:memory-update` 让观察器扫描你的执行历史
2. 运行 `/project:skill-review` 审核生成的候选
3. 提交 PR，包含候选文件和对应的验证测试

---

## 许可证

MIT