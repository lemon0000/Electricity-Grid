# RQ2 论文路线图与导航页

创建日期：2026-08-20  
适用范围：毕业论文/期刊投稿主线 = RQ2（网络条件服务与小时级CFE共享业务灵活性预算）。  
本页是导航与状态映射，不重述已冻结的科学契约。权威来源仍是 `agent.md`（范围/路由/审查；§4 已将 RQ2 定为首篇主创新、RQ1 降为后续扩展）、`docs/model_spec/formulation.md`（数学规格）、`docs/model_spec/blocker_register.md`（阻塞状态）与 `docs/literature/`（文献与缺口）。

> 定位约束（来自 `agent.md` 与 project_memory）：RQ2 不改写冻结的 B3/B4/B5 基线与 repair-010 认证链；本机只做代码+单测，正式长求解与预注册留给执行机 + 用户授权。

---

## 1. RQ2 一句话卖点

现实中数据中心的两类服务是**分开签约、分开触发**的——网络条件削减是对 N-1 事件的被动事后响应，小时级 CFE 移峰是跟随绿电的主动事前调度——但二者抽取自**同一业务柔性物理包络**。规划者若按各自“可用灵活性”分别签出条件容量 X，就会在**时序维度**（持续时间、事件次数、恢复债务）重复占用同一包络。RQ2 用**共享时序包络 + B6 重复承诺错误基线 + 场景外 CVaR** 量化这种高估幅度与履约失败概率。

## 2. 三层创新与对应可证伪命题

| 层 | 创新点 | 可证伪命题 | 判据（在结果前冻结） |
|---|---|---|---|
| 机制 | 共享时序包络（MW+持续时间+事件次数+累计能量+恢复功率+恢复债务） | H1：正确共享包络会拒绝 B6 分离预算仍认证的 X 水平 | 存在 X*，使 B6 认证而共享模型不可行；差额 = X 高估量 |
| 概念 | B6 允许重复承诺的错误基线 | H2：B6 策略在场景外执行时产生正的持续时间违约/恢复债务/失败概率 | 场景外既定策略执行下，B6 的违约指标显著大于共享模型（同输入同安全集） |
| 评估 | 场景外 service-CVaR 尾部风险 + λ/κ/β 敏感性 | H3：随 λ^risk 增大，最优在“期望成本↔尾部服务损失”上呈单调权衡且方法排序稳健 | ε-约束 Pareto 前沿与 λ 扫描给出稳定排序，非单点权重产物 |

H1/H2/H3 必须在**相同输入、相同场景、相同安全集**下比较；VMA/高估量接近零或错误基线不劣的区域也必须如实报告（`agent.md` §9 公平性）。

## 3. 现有资产 → RQ2 映射（已实现，本机可复核）

| RQ2 要素 | 代码/规格 | 测试 | 状态 |
|---|---|---|---|
| 共享 MW 预算 + B6 分离预算 | [deterministic_fx.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/models/deterministic_fx.py) `SharedFlexibilityBudget`；`formulation.md` §8、§10.1 | [test_shared_flexibility_budget.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_shared_flexibility_budget.py) | mechanism-only（合成参数） |
| 恢复债务 / 持续时间 / 事件数包络 | `formulation.md` §10.2、§10.3；[flexibility_envelope.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/evaluation/flexibility_envelope.py) | [test_flexibility_envelope.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_flexibility_envelope.py) | mechanism-only（F1-F3 门，F3 因恢复债务失败＝阳性结果） |
| service-CVaR 尾部风险 | `formulation.md` §13；[service_risk.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/evaluation/service_risk.py) `evaluate_service_cvar` | [test_service_cvar.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_service_cvar.py) | 后处理度量（未接入优化目标） |
| 场景外既定策略执行 | [stochastic_policy.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/evaluation/stochastic_policy.py)；`formulation.md` §12 | [test_stochastic_holdout_policy.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_stochastic_holdout_policy.py) | 合成 holdout（非经验 VMA） |

结论：RQ2 的**度量层与错误基线已成型且有测试**，是本项目中数据风险最低、对照最干净的部分。缺的是把 CVaR 与共享预算接入一个**独立的经济随机优化目标**（下节 L5）并做场景外量化。

## 4. 待建：L5 经济随机模型（R3 任务）

- 目标：`min C^grid + C^op + λ^risk · CVaR_β(L)`，共享时序包络作硬约束（`formulation.md` §13、§14）。
- 边界：**新建独立模块**（如 `src/models/economic_stochastic.py`），复用现有场景树 API 与 §8/§10/§13 约束；不改写冻结的 B3/B4/B5 与 repair-010。
- 阻塞规避：L5 作为新功能，可独立预注册与求解，绕开 repair-010 的 calibration 阻塞链（见 `blocker_register.md`）。
- TDD 顺序（对应 pending 任务 #4–#8）：精读现有随机模型 Pyomo 惯例与场景树 API → 写失败测试 → 实现模块 → 窄范围测试+不变量自检 → `sol_reviewer` 独立审查。
- 实验设计：H1 用共享 vs B6 的 X 高估量；H2 用场景外既定策略执行的违约/债务/失败率；H3 用 λ 扫描 + ε-约束 Pareto。种子固定并记录（`agent.md` §10）。

## 5. 目标期刊评估：RQ2 单独发 TSG 是否够？

结论：**度量层与错误基线的组合具备 TSG 级别的“机制+证据”骨架，但当前工作量偏单薄，需补齐三块才不至于被判为“一条约束 + 一个 CVaR 后处理”。**

必须补齐（缺一即偏薄）：

1. **L5 闭环 + 场景外量化**：把共享预算与 CVaR 接入统一经济目标，给出 H1/H2/H3 的定量结果（X 高估 %、场景外失败概率、Pareto 前沿），而非仅机制门。这是从“实现了约束”到“回答了 RQ”的关键跨越。
2. **敏感性与稳健性**：λ/κ/β 扫描 + 种子重复，证明结论非单点参数产物；同时如实标注合成参数边界（不冒充工程认证）。
3. **正面回应最近邻竞争**：在引言/相关工作中显式区分 DC04/DC11/DC12 的“统一变量天然不重复”，把 RQ2 定位为“契约分离导致的重复承诺量化”（见 `research_gap.md` §缺口边界 2）。

加分但非必需：多 POI 或 RTS-GMLC 规模上的重复承诺敏感性；与 RQ1（多阶段自适应）的一条对照，说明重复承诺风险在自适应策略下是否被放大或缓解。

风险提示（审稿人最可能攻击）：
- “统一调度模型不会重复承诺，为何研究重复？”——已在 `research_gap.md` 预答（契约与触发分离 + 时序维度冲突）。
- “合成参数能否支撑履约风险结论？”——只能作机制与敏感性证据，论文措辞不得升级为工程/合同认证（`agent.md` §8 硬约束）。
- “CVaR 只是后处理还是进入决策？”——L5 必须把 CVaR 接入目标，否则评估创新站不住。

## 6. 与硬约束的一致性检查

- 共享预算 `c_grid + c_green ≤ D_flex`、恢复债务不凭空消失、CVaR 只用于服务/业务损失、`y_CFE` 只表同小时可归属——均为 `agent.md` §8 硬约束，L5 不得放松。
- 本机不启动长求解；正式运行与预注册留给执行机 + 用户授权（`AGENTS.md`、project_memory）。

## 7. 文件与结构约定（RQ2 视角）

- 文献：`docs/literature/literature_matrix.csv`（新增 DC11/DC12/DC13/FLEX09）、`research_gap.md`（缺口边界 2 已强化）、`search_protocol.md`（2026-08-20 查新记录）。
- 规格：`formulation.md` §8/§10/§13/§14 为 RQ2 数学权威。
- 计划：本页为 RQ2 导航；总执行步骤仍见 `docs/plan/科研项目执行步骤.md`。
- 论文产物：`paper/drafts`、`paper/figures`、`paper/tables`（当前为空，待 L5 结果固定后填充）。
