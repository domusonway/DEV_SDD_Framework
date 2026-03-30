````markdown
# Memory INDEX — DEV SDD Framework v3.1
# 启动必读 | 目标：60 秒内扫完，按需展开

---

## ⚡ CRITICAL（5条，全部内联到 CLAUDE.md，此处存档）

| ID | 一句话规则 | 适用场景 | 详情 |
|----|-----------|---------|------|
| MEM_F_C_001 | 校验器必须先用参考输出自测才能交付 | validation | [→](critical/MEM_F_C_001.md) |
| MEM_F_C_002 | SPEC 接口必须明确 dtype（bytes/str/int） | spec_writing | [→](critical/MEM_F_C_002.md) |
| MEM_F_C_003 | 测试失败只改实现，禁改断言禁 skip | tdd_impl | [→](critical/MEM_F_C_003.md) |
| MEM_F_C_004 | socket recv 必须精确捕获三类异常 | network_code | [→](critical/MEM_F_C_004.md) |
| MEM_F_C_005 | recv 返回 b'' = 连接关闭，必须检查 | network_code | [→](critical/MEM_F_C_005.md) |

> CRITICAL 已内联到 CLAUDE.md，读到主入口即激活。

---

## 📚 IMPORTANT（按需加载，context-probe 自动匹配）

### 网络 / TCP 编程
| ID | 一句话规则 | 文件 |
|----|-----------|------|
| MEM_F_I_001 | 集成测试客户端也须捕获 ConnectionResetError | [→](important/MEM_F_I_001.md) |
| MEM_F_I_002 | socketpair 比真实 socket 更适合单元测试 | [→](important/MEM_F_I_002.md) |
| MEM_F_I_003 | MockSocket 会掩盖隐式契约 Bug，E2E 才能发现 | [→](important/MEM_F_I_003.md) |

### 跨语言重构
| ID | 一句话规则 | 文件 |
|----|-----------|------|
| MEM_F_I_004 | C int fd → Python socket 对象，size 参数省略 | [→](important/MEM_F_I_004.md) |
| MEM_F_I_005 | C fork+execl → Python subprocess.Popen（多线程安全）| [→](important/MEM_F_I_005.md) |

### TDD 流程
| ID | 一句话规则 | 文件 |
|----|-----------|------|
| MEM_F_I_006 | RED 阶段先确认 FAIL，直接 PASS = 测试写错了 | [→](important/MEM_F_I_006.md) |
| MEM_F_I_007 | 共享状态用 RLock，不用 Lock（防同线程递归死锁） | [→](important/MEM_F_I_007.md) |

---

## 🗂️ 领域记忆（项目启动时按领域选择加载）

| 领域 | 加载时机 | 入口 |
|------|---------|------|
| HTTP 网络编程 | 涉及 HTTP 协议实现 | [memory/domains/http/INDEX.md](domains/http/INDEX.md) |
| TDD 模式 | TDD 失败 / 测试设计问题 | [memory/domains/tdd_patterns/INDEX.md](domains/tdd_patterns/INDEX.md) |
| 类型安全 | bytes/str/类型错误 | [memory/domains/type_safety/INDEX.md](domains/type_safety/INDEX.md) |
| 并发编程 | threading/asyncio/锁 | [memory/domains/concurrency/INDEX.md](domains/concurrency/INDEX.md) |

---

## 🔬 候选规则区（Meta-Skill Loop，v3.1 新增）

> 此区域记录已通过 2+ 项目验证但尚未正式提升的候选规则。
> 正式提升后从此区移除，写入上方对应分区。
> 详细信息见 `memory/candidates/` 目录。

**查看全部候选**：
```bash
python3 .claude/tools/skill-tracker/tracker.py candidates
```

**审核并提升**：`/project:skill-review`

**变更历史**：[memory/skill-changelog.md](skill-changelog.md)

---

## 📋 加载决策树（v3.1：context-probe 自动执行，此处为备查）

```
任务到来
  │
  ├─ 【自动】执行 context-probe skill 匹配关键词
  │    → 自动加载匹配的 IMPORTANT 条目（上限4条）
  │    → 检查 candidates/ 预警（validated_projects ≥ 2）
  │
  ├─ 涉及 socket/recv/send？
  │    → context-probe 自动加载 MEM_F_I_001, MEM_F_I_002
  │
  ├─ 涉及 asyncio/aiohttp？
  │    → context-probe 自动加载 domains/concurrency/INDEX.md
  │
  ├─ C → Python 重构？
  │    → context-probe 自动加载 MEM_F_I_004, MEM_F_I_005
  │
  ├─ HTTP 协议实现？
  │    → context-probe 自动加载 domains/http/INDEX.md
  │
  ├─ TDD RED 超过 2 次？
  │    → 触发 diagnose-bug skill，不需要加载更多记忆
  │
  └─ 其他 → CRITICAL 内联已足够，直接开始
```

---

## 统计与健康

```
CRITICAL : 5 条（门槛：≥3 个项目独立验证）
IMPORTANT: 7 条（门槛：1 个项目验证，季度审查）
领域记忆 : 4 个域（http / tdd_patterns / type_safety / concurrency）
候选规则 : 见 memory/candidates/ 目录
上次审查 : 2026-03-05
下次审查 : 2026-09-05
框架版本 : v3.1（加入 Meta-Skill Loop 全类型自进化）
```

> CRITICAL 膨胀预警：超过 7 条需审查合并。
> IMPORTANT 老化预警：超过 90 天未触发的条目候选归档。
> 候选积压预警：pending_review 超过 15 条时运行 /project:skill-review。

````
