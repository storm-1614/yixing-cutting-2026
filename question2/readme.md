# 子问题 2：每工件 ≥10 件，最大化总收益

> 2026 年「亿星软件杯」数学建模竞赛 A 题

## 目录结构

```
question2/
│
├── 📄 ems_solver_optimal.py        ← ★ 最终求解器 (727,990 利润)
├── 📄 ems_solver_subproblem2.py    ← 原版求解器 (681,750 利润)
├── 📄 ems_solver_v2.py             ← 失败的 v2 尝试 (649,080, 已弃用)
│
├── 📄 algorithm_tutorial.md        ← ★ 算法教学文档 (从零讲解)
├── 📄 algorithm_tutorial.pdf       ← 教学文档 PDF 导出
├── 📄 algorithm_flow.excalidraw    ← 算法流程图 (Excalidraw 可编辑)
├── 📄 algo.png                     ← 算法流程图 PNG 导出
│
├── 📄 ems_subproblem2_v2_model.md  ← 算法设计论文 (数学模型 + 实验)
├── 📄 ems_subproblem2_model.md     ← 原版算法论文
│
├── 📄 export_result2.py            ← 运行求解器并导出到 Excel
├── 📄 result2.xlsx                 ← 导出结果 (生产计划表)
│
└── 📄 readme.md                    ← 本文件
```

## 文件说明

### 求解器

| 文件 | 利润 | 利用率 | 状态 |
|------|------|--------|------|
| `ems_solver_optimal.py` | **727,990** | 91.41% | **最终版本** |
| `ems_solver_subproblem2.py` | 681,750 | 87.22% | 原版，已淘汰 |
| `ems_solver_v2.py` | 649,080 | — | 单阶段尝试，失败，仅留作参考 |

`ems_solver_optimal.py` 算法核心：**多策略两阶段 EMS 贪心构造 + 破坏-重建迭代局部搜索 (ILS)**。

- 构造阶段：48 次独立试验，5 种 Phase 1 排序策略轮换
- ILS 阶段：800 轮破坏-重建，偏置销毁低利润密度工件，仅接受改善
- 运行方式：`python3 ems_solver_optimal.py`

### 教学文档

| 文件 | 内容 |
|------|------|
| `algorithm_tutorial.md` | 从零开始的算法教学，含每个步骤的代码引用和数值示例 |
| `algorithm_tutorial.pdf` | 同上，PDF 格式 |
| `algorithm_flow.excalidraw` | 算法流程总图，拖入 [excalidraw.com](https://excalidraw.com) 可编辑 |
| `algo.png` | 流程图 PNG 导出 |

### 论文

| 文件 | 内容 |
|------|------|
| `ems_subproblem2_v2_model.md` | 最终算法的数学模型、设计原则、实验结果 |
| `ems_subproblem2_model.md` | 原版算法文档，保留作对比参考 |

### 结果导出

`export_result2.py` 运行 `ems_solver_optimal.py` 并将每块原材料的工件数量填入 `result2.xlsx` 模板。

```bash
python3 export_result2.py
```

## 最优结果摘要

| 指标 | 数值 |
|------|------|
| 总利润 | 727,990 |
| 材料利用率 | 91.41% |
| 占理论利润上界 | 86.27% |
| 总工件数 | 551 |
| 运行时间 | ~109s |

| 工件 | 尺寸 | 利润密度 | 产量 |
|------|------|---------|------|
| J01 | 40×40×40 | 0.00969 | 11 |
| J02 | 50×40×40 | 0.00975 | 15 |
| J03 | 60×50×30 | 0.00978 | 24 |
| J04 | 75×60×40 | 0.01028 | 23 |
| J05 | 80×60×50 | 0.01050 | 180 |
| J06 | 100×50×20 | 0.01000 | 68 |
| J07 | 120×20×20 | **0.01125** | **230** |

## 快速开始

```bash
# 运行求解器 (约 2 分钟)
python3 ems_solver_optimal.py

# 导出到 Excel
python3 export_result2.py

# 阅读算法文档
open algorithm_tutorial.md
```
