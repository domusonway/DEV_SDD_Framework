# sdd-tinyhttpd · 实现计划

---

## 依赖图
```
request_parser（无依赖）
response（无依赖）
router（无依赖）
static_handler（依赖 response）
cgi_handler（依赖 response）
server（依赖全部）
```

## 实现批次

### 批次 1（无依赖，可并行）
- [ ] request_parser — 估算: M
- [ ] response — 估算: L
- [ ] router — 估算: L

### 批次 2（依赖 response）
- [ ] static_handler — 估算: M
- [ ] cgi_handler — 估算: M

### 批次 3（依赖全部）
- [ ] server — 估算: H

---

## 里程碑

| 里程碑 | 条件 | 目标 |
|--------|------|------|
| M1 解析层 | 批次1全绿 | 批次2开始前 |
| M2 处理层 | 批次2全绿 | 批次3开始前 |
| M3 完整服务器 | 批次3全绿 | 手动 curl 测试 |
| M4 交付就绪 | E2E 测试 + validate-output 通过 | 项目完成 |
