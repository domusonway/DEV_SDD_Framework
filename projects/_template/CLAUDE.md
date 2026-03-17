```markdown
# {{PROJECT_NAME}} · 项目上下文入口
> 创建日期: {{DATE}} | 复杂度: {{COMPLEXITY}} | 工作模式: {{MODE}}

---

## 项目简介
{{PROJECT_DESCRIPTION}}

---

## 技术栈
- 语言: {{LANGUAGE}}
- 测试框架: {{TEST_FRAMEWORK}}
- 主要依赖: {{DEPENDENCIES}}

---

## 项目特有约束（覆盖框架默认规则时在此声明）

<!-- 示例：
- 此项目使用 asyncio，所有 socket 操作改用 asyncio 协议
- 响应格式为 JSON bytes，不是 HTTP 协议
-->

---

## 模块列表

| 模块 | 路径 | SPEC | 状态 |
|------|------|------|------|
| {{MODULE_1}} | modules/{{MODULE_1}}/ | [SPEC](modules/{{MODULE_1}}/SPEC.md) | 🔴 未开始 |

---

## 按需加载地图（项目级补充）

| 场景 | 读取路径 |
|------|---------|
| 项目背景 | `docs/CONTEXT.md` |
| 当前进度 | `docs/TODO.md` |
| 项目记忆 | `memory/INDEX.md` |
| 上次会话 | `memory/sessions/` 最新文件 |

---

## 验收标准
{{ACCEPTANCE_CRITERIA}}

```

