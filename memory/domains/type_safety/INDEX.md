# Type Safety 领域记忆 · 索引
> 加载时机：涉及 bytes/str/int/dict 类型错误、SPEC dtype 约定、类型注解时

---

## 快速规则表

| ID | 规则 | 来源 |
|----|------|------|
| MEM_D_TYPE_001 | SPEC 接口表必须明确每个返回值的 dtype（bytes/str/int），不可含糊 | MEM_F_C_002 |
| MEM_D_TYPE_002 | socket.sendall() 只接受 bytes，response 模块返回 str 会在 E2E 才爆 | P_THD_001 |
| MEM_D_TYPE_003 | Content-Length 必须用 len(body_bytes) 而非 len(body_str) | MEM_D_HTTP_003 |
| MEM_D_TYPE_004 | AST check_contract.py 专门检测 bytes vs str 返回类型不匹配 | observe-verify |

---

## 候选规则区

（暂无）

---

## 跨域关联
- 与 network 领域强关联：网络代码是类型错误的高发区
- 与 tdd_patterns 关联：类型错误常被 MockSocket 掩盖，只在 E2E 发现
