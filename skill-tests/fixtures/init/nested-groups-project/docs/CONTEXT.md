# Nested Groups Project · 项目背景与架构

---

## 项目目标
验证 INIT 可以从带分组标题的模块划分中提取细粒度可执行模块。

---

## 背景
该项目把 backend/frontend 作为说明性分组，真正可执行模块定义在 `####` 子标题中。

---

## 技术栈
- 语言: Python 3.11
- 测试框架: pytest
- 主要依赖: fastapi, streamlit

---

## 模块划分

### backend/
后端模块：

#### projects
- 职责：项目 CRUD
- 输入：ProjectCreate
- 输出：ProjectResponse
- 依赖：无

#### config
- 职责：配置加载
- 输入：环境变量
- 输出：Settings
- 依赖：无

#### workorders
- 职责：工单聚合查询
- 输入：workorder_id
- 输出：WorkOrderDetail
- 依赖：projects, config

### frontend/
前端模块：

#### dashboard
- 职责：展示项目和工单信息
- 输入：Repository 数据
- 输出：Streamlit 页面
- 依赖：projects

---

## 验收标准
- INIT 生成的计划只包含细粒度可执行模块
- backend/frontend 分组不会被错误写入 `docs/plan.json`
