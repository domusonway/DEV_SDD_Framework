# Impl Paths Project · 项目背景与架构

---

## 项目目标
验证 INIT 能把规格路径和实现路径分开建模，并从目录结构推断真实实现位置。

---

## 背景
该项目的规格文档放在 `modules/`，但代码实现位于 `harness/` 和项目根目录的 `cli.py`。

---

## 系统结构总览

### 目录结构

```text
project/
├── harness/
│   ├── models.py
│   └── dataset.py
├── cli.py
└── docs/
    └── CONTEXT.md
```

---

## 技术栈
- 语言: Python 3.11
- 测试框架: pytest
- 主要依赖: stdlib only

---

## 模块划分

### models
- 职责：定义共享数据模型
- 输入：原始 case 和 run 数据
- 输出：结构化 dataclass
- 依赖：无

### cli
- 职责：提供命令行入口
- 输入：命令行参数
- 输出：退出码与终端输出
- 依赖：models

---

## 验收标准
- plan.json 中模块必须同时拥有 spec_path 与 impl_path
- CLAUDE.md 中的 SPEC 链接不能由实现路径拼接得出
