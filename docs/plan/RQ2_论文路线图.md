# RQ2 论文路线图与导航页

创建日期：2026-08-20  
适用范围：毕业论文/期刊投稿主线 = RQ2（网络条件服务与小时级CFE共享业务灵活性预算）。  
本页是导航与状态映射，不重述已冻结的科学契约。权威来源仍是 `agent.md`（范围/路由/审查；§4 已将 RQ2 定为首篇主创新、RQ1 降为后续扩展）、`docs/model_spec/formulation.md`（数学规格）、`docs/model_spec/blocker_register.md`（阻塞状态）与 `docs/literature/`（文献与缺口）。

> 定位约束（来自 `agent.md` 与 project_memory）：RQ2 不改写冻结的 B3/B4/B5 基线与 repair-010 认证链；本机只做代码+单测，正式长求解与预注册留给执行机 + 用户授权。
>
> 2026-08-25 scope amendment：本页保留早期显式X研究蓝图。当前公开边缘
> v6 successor的直接estimand是`normalized minimum flexibility
> underprovisioning`，不是X高估；E0、条件transport、共同coupling与执行机
> 门禁以`RQ2_公开数据鲁棒识别路线图_v6.md`为准。

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
| **L5 经济随机模型（CVaR 进目标）** | [economic_stochastic.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/models/economic_stochastic.py) `solve_economic_stochastic`；`formulation.md` §12-14 | [test_economic_stochastic.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_economic_stochastic.py) | mechanism-only（共享预算+B6+§13 CVaR 进 §14 目标） |
| **L5 正式入口（λ 扫描 + H1/H3）** | [run_rq2_l5_economic_stochastic.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/experiments/run_rq2_l5_economic_stochastic.py)；[rq2_l5_economic_stochastic.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/rq2_l5_economic_stochastic.yaml) | [test_rq2_l5_runner.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_rq2_l5_runner.py) | 本机微型合成算例自检通过；正式规模求解留执行机 |
| **RTS-24 物理派生 `grid_need`（A/B）** | [network_grid_need.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/grid/network_grid_need.py)；[rq2_network_grid_need.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/models/rq2_network_grid_need.py)；入口 [run_rq2_l5_economic_network.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/experiments/run_rq2_l5_economic_network.py) | [test_rq2_network_grid_need.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_rq2_network_grid_need.py) | mechanism-only；A=逐状态最小削减，B=outage-topology POI PTDF 过载折算；Bus 8、selected sustained N-1、恒 `security_certified=false` |
| **时序包络进入 L5 recourse** | [economic_temporal_stochastic.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/models/economic_temporal_stochastic.py)；入口 [run_rq2_l5_economic_temporal_network.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/experiments/run_rq2_l5_economic_temporal_network.py) | [test_economic_temporal_stochastic.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_economic_temporal_stochastic.py)、[test_rq2_l5_temporal_network_runner.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_rq2_l5_temporal_network_runner.py) | mechanism-only；共享 `on/start/stop/q/recovery` MIP，B6 分离双包络并回放真实合计轨迹 |
| **Temporal H2 固定策略 holdout** | [temporal_economic_holdout.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/evaluation/temporal_economic_holdout.py)；入口 [run_rq2_h2_temporal_holdout.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/experiments/run_rq2_h2_temporal_holdout.py)；三来源入口 [run_rq2_h2_temporal_source_ablation.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/experiments/run_rq2_h2_temporal_source_ablation.py) | [test_temporal_economic_holdout.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_temporal_economic_holdout.py)、[test_temporal_trace_scenario_generator.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_temporal_trace_scenario_generator.py)、[test_temporal_scenario_reduction.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_temporal_scenario_reduction.py) | manual/generated/reduced chronology mechanism-only；固定`D_flex`、共享holdout、时序距离缩减、failure-channel与right-censoring诚实报告 |
| **H2 场景外既定策略执行（钉死 D^flex）** | [economic_holdout.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/evaluation/economic_holdout.py) `evaluate_economic_holdout`；正式入口 [run_rq2_h2_stochastic_holdout.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/experiments/run_rq2_h2_stochastic_holdout.py)（读 [rq2_h2_stochastic_holdout.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/rq2_h2_stochastic_holdout.yaml)）；`formulation.md` §12 | [test_economic_holdout.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_economic_holdout.py)、[test_rq2_h2_runner.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_rq2_h2_runner.py) | 本机微型合成 holdout 自检通过；正式规模留执行机 |

结论：RQ2 的**度量层、错误基线、L5 经济随机目标与 H2 场景外量化均已成型且有测试**，是本项目中数据风险最低、对照最干净的部分。CVaR 与共享预算已接入统一经济目标（`min C^grid + C^op + λ·CVaR_β(L)`），并由正式入口在 λ 扫描下给出 H1（B6 高估量）与 H3（成本↔尾部风险单调权衡）；H2 入口把 L5 规划出的 correct/B6 两个 `D^flex` 钉死后在未见 holdout 场景上按真实共享预算执行，量化 B6 的场景外欠交付（失败概率 + 期望缺口，含硬安全不可行）。缺的是在执行机上跑更大规模的正式算例。

### 3.1 三区域叙事重构（2026-08-24）

RTS-GMLC CFE successor显示：单一100%小时目标可能使correct与B6同时进入共同不足，不能继续把“B6总是增加场景外风险”作为预设主结论。首篇叙事改为识别以下三个运行区域及边界：

- `R1_no_conflict`：两策略均成功且结果等价；
- `R2_double_commitment_risk`：B6容量低配或场景外服务严格更差；
- `R3_common_insufficiency`：两模型均不可行或在共享执行下等价失败。

方向冲突与solver未决分别保留为`diagnostic_mixed`和`unresolved`，不得强制归类。恢复尾部继续读取连续RTS-GMLC CFE小时，恢复功率只能使用超过小时目标的CFE-compatible headroom，防止延期业务逃离CFE核算。冻结设计、70-cell实验矩阵与完整报告规则见：

- `configs/rq2_three_region_phase_map_preregistration_v1.yaml`；
- `configs/rq2_three_region_phase_map_v1.yaml`；
- `docs/plan/RQ2_三区域相图实验清单.md`；
- `paper/drafts/RQ2_three_region_narrative.md`。

冻结benchmark已完成：70/70 cells、计算门通过，但结果为
`R1=0, R2=0, R3=69, mixed=1, unresolved=0`。因此该设计没有识别出三区域边界，也不支持数据驱动时序下的稳健H2。首篇TSG投稿继续阻塞；后续不得在看过该结果后调整同一网格寻找R2，只能依据外部合同/恢复数据注册新验证，或把论文主问题改为严格小时CFE下的共同不足边界。

## 4. L5 经济随机模型：入口已建，待正式求解（R3 任务）

- 目标：`min C^grid + C^op + λ^risk · CVaR_β(L)`，共享 MW 预算作硬约束（`formulation.md` §13、§14）。**已实现并进目标**（非后处理）。
- 边界：**独立新模块** [economic_stochastic.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/models/economic_stochastic.py)，复用现有 §8/§10/§13 约束语义与 §13 服务损失系数；不改写冻结的 B3/B4/B5 与 repair-010。
- 阻塞规避：L5 作为新功能，可独立预注册与求解，绕开 repair-010 的 calibration 阻塞链（见 `blocker_register.md`）。
- 已完成（对应任务 #4-#8）：精读 API → TDD（模型 15 例 + 入口 12 例）→ 实现模块与正式入口 → 本机窄范围测试+不变量自检（CVaR 与 §13 独立 evaluator 交叉校验、fail-closed）→ 待 `sol_reviewer` 独立审查。
- 正式入口：`experiments/run_rq2_l5_economic_stochastic.py`（读 `configs/rq2_l5_economic_stochastic.yaml`），产出 `results/tables/rq2_l5_economic_stochastic_v1/{runs,frontier}.csv` 与 `summary.json`（内嵌 provenance 与诚实标签）。本机仅用微型合成算例验证管道与不变量，不落盘 canonical 结果；正式规模算例保持同 schema、由执行机打标签运行。
- 实验设计：H1 用共享 vs B6 的 X 高估量（入口 `h1_overestimation_mw`）；H2 用场景外既定策略执行的违约/债务/失败率（**已建**，见下）；H3 用 λ 扫描 + ε-约束 Pareto（入口 `frontier`）。种子固定并记录（`agent.md` §10；本增量为确定性 LP，`random_seed=null`）。

### 4.1 H2 场景外既定策略执行：入口已建、R3 复审 3 项已修复，待正式求解

- 目标：验证 §12 的场景外命题——B6 重复承诺错误规划出的 `D^flex`，在未见 holdout 场景上按**真实共享预算**执行时，服务欠交付幅度严格大于正确共享模型（更高失败概率 + 更大期望缺口，含硬安全不可行），在同一输入/场景/安全集下（`agent.md` §9 公平性）。
- 识别策略（两阶段、既定策略）：① **规划（样本内）** 在训练场景树上分别解 L5 的 correct（`enforce_joint_budget=True`）与 B6（`False`）模型，读出各自首阶段非预见性 `D^flex`（correct ≥ B6，即 H1）；② **执行（样本外）** 把 `D^flex` **钉死**（不再优化 → 非预见性），在每个未见叶上仅解 recourse，且执行物理**恒为真实共享预算** `c_grid + c_green + l_drop ≤ D^flex`（B6 的错误只在规划期，执行期物理共享）。B6 欠配的预算无法同时服务两类需求 → 缺口；硬网络削减需求超过钉死预算的叶 → recourse 不可行（诚实上报为硬安全失败）。
- 边界与复用：recourse 复用**同一** `solve_economic_stochastic` 模型（新增 `fixed_flexibility_mw` 钉死首阶段 + `enforce_joint_budget=True`），“同一安全集”是结构性保证而非口头断言。**不**走 `stochastic_policy.py`（那是 RQ1 B3/B4 的 F/X 多阶段 107 状态 RTS-24 holdout，策略语义不同）。场景外失败只在 MW 预算维度度量；恢复债务/持续时间/事件次数时序包络与 L5 一致，暂不在范围内（`certification_blockers` 已标注）。
- 已完成（对应任务 #14-#18）：精读 L5/service_risk API → 实现核心模块 `evaluate_economic_holdout` 与正式入口 → TDD（核心 15 例 + 入口 12 例 + 模型钉死 3 例）→ 本机窄范围测试（上一会话 70 例全过）+ 不变量自检（holdout CVaR 与 §13 独立 evaluator 交叉校验=0、真实共享预算约束、非预见性、fail-closed）→ `sol_reviewer` 独立 R3 审查完成。
- R3 审查结论（2026-08-21）：**PASS-WITH-COMMENTS**。审查逐一手工复算了冻结工件全部关键数字（承诺 D^flex、逐叶 dispatch/loss、失败概率、期望缺口、correct 策略 β=0.5 CVaR），与 `summary.json`/`leaves.csv`/`policies.csv` **完全一致**；硬约束（`c_grid≥grid_need` 从不与 CVaR 交易）、非预见性、真实共享预算执行、诚实标签均正确落地。冻结算例在其构造点上正确且诚实。
- 复审 3 项已修复并回归通过（2026-08-21，本机 conda `compute` 环境 Python 3.11.15 + pyomo 6.10.1/highspy 1.15.1/pytest 9.0.2）：
  - ① **假阴性（finding 1）**：硬失败叶现把整段未服务 green call 记为 access-shortfall 能量并计入 `expected_access_shortfall_mwh`；硬/软失败**概率通道保持互斥**（硬失败叶 `service_shortfall_failure=False`，`total = hard + soft`），杜绝"硬失败叶 + correct 同叶可行有缺口"下的假阴性。冻结算例 B6 期望缺口由 14→42 MWh（严格 > correct 14 MWh），H2 仍为真。回归：`test_hard_failure_leaf_counts_as_shortfall_energy`、`test_hard_and_soft_probability_channels_are_disjoint`。
  - ② **诚实性映射（finding 2）**：`EconomicStochasticResult` 新增 `proven_infeasible`，仅 `TerminationCondition.infeasible` 置真；超时/数值失败/`infeasibleOrUnbounded` 等均 `feasible=False` 且 `proven_infeasible=False` 并保留真实终止串。holdout `_execute_leaf` 据此区分：未决 recourse 走独立 `solver_unresolved` 通道，绝不铸成硬安全失败或阳性 H2。回归：`test_timeout_is_unresolved_not_proven_infeasible`、`test_unresolved_recourse_is_not_a_hard_failure`。
  - ③ **独立交叉校验（finding 3）**：runner 的 CVaR 交叉校验改为自含闭式 `_independent_service_cvar`（直接从 dispatch 能量与 κ 重算，不再调用 `evaluate_service_cvar`），是真正独立复算。回归：`test_independent_service_cvar_matches_hand_calculation`（手算 CVaR=120）、`test_cross_check_detects_a_corrupted_reported_cvar`（篡改上报值可被门捕获并 fail-closed）。
- 本机环境状态：开发机改用 conda `compute` 环境（Python 3.11.15 + pyomo 6.10.1/highspy 1.15.1/pytest 9.0.2/scipy/pypower/osqp/casadi/openpyxl 等，与 `requirements.txt` 固定版本一致；临时 `.venv` 已删除）。三份受影响测试文件 50 例全过（其中 R3 三项修复对应 7 例专项复核通过），H2 入口以模块方式重跑并重新落盘工件。正式规模算例仍保持同 schema、由执行机打标签运行。
- 正式入口：`experiments/run_rq2_h2_stochastic_holdout.py`（读 `configs/rq2_h2_stochastic_holdout.yaml`），产出 `results/tables/rq2_h2_stochastic_holdout_v1/{leaves,policies}.csv` 与 `summary.json`（内嵌 provenance 与诚实标签，`security_certified=false`、`formal_vma_published=false`）。本机仅用微型合成 holdout 验证管道与不变量，不落盘 canonical 结果；正式规模算例保持同 schema、由执行机打标签运行。
- fail-closed 语义：训练规划不可行 → 门失败（`gate_passed=false`）；holdout 叶的硬安全不可行是**阳性 H2 证据**，不触发 fail-closed（否则会把 B6 的场景外失败误判为管道错误）。

### 4.2 数据驱动生成式场景（P0，AI 融入点）：本机已建生成器，待接入 H2 入口

- 决策与定位（2026-08-22，用户决策）：不盯死 TSG，投**任一中科院一区 IEEE Trans**（TSG/TSTE 优先，均为一区/JCR Q1）；AI 元素以 **P0 生成式场景生成器**落地，作为**不确定性建模工具**服务 RQ2 主机制，**不进入安全认证层**。DFL（预测-决策一体化）作为可选升格增量（冲 TPWRS），本轮不做。
- 动机（审稿软肋）：现有 H2 的 training/holdout 是**手工冻结树**，必被质疑"高估幅度/失败概率是手搓场景的产物"。生成器用项目已有的**真实 AI 负载 trace 形状**驱动场景，直接回应"参数全合成/单参数产物"。
- 实现：[trace_scenario_generator.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/scenarios/trace_scenario_generator.py) `generate_holdout_scenarios`，仅依赖 numpy+scipy+stdlib（与 `requirements.txt` 一致，未引入 pandas）。
  - **两条真实 trace 各驱动一个维度**：Google PowerData 2019 归一化 PDU 功率利用率形状 → 网络胁迫 `grid_need_mw`；Alibaba PAI GPU 2020 相对小时工作量形状（`peak_normalized` 显式归一化）→ 绿电/CFE 调用 `green_call_mw`。
  - **归一化无 holdout 泄漏（split-aware）**：派生 MW = `frozen_scale × mean(normalized_window)`，而 `mean(v/peak)=mean(v)/peak`，故除数（peak）为所有窗口共享。若用**全序列全局峰值**（含 holdout 段、峰值可能落在 holdout）归一化，training 场景 MW 会经共享除数间接依赖 holdout 小时——样本外泄漏。Google 数据卡明确禁止（`normalization_uses_future_window_peak=true`、`normalization_allowed_use=fixed_replay_not_train_or_holdout_feature`：全窗峰值“must not be calculated across a train/holdout split”）。修法：`TraceShape.peak_normalized` **拒绝裸全局峰值**（fail-closed），只接受二选一除数——① `split_fraction`：峰值仅从 training 段 `[0, split)` 估计并统一施用于全段（holdout 若超训练峰值则诚实 >1，不裁剪）；② `external_peak`：投前冻结常数（无 holdout 依赖）。生成器另加**结构守卫**：断言形状归一化所用 `split_fraction` 与本次抽样 `split_fraction` 一致，否则拒绝；`provenance.normalization` 记录除数与其估计 split，供逐条复核。
  - **块自助采样（block bootstrap）**：在 trace 内取连续窗口聚合，保留 trace 内部时序自相关（`relative_intervals_preserved=true`），优于逐时 i.i.d. 抽样。
  - **样本外分离是结构性保证**：每条 trace 在时间轴按 `split_fraction` 单点切分，training 窗口取自早段 `[0, split)`、holdout 取自晚段 `[split, T)`，窗口为连续块 → **无 source 小时共享**（测试 `test_train_and_holdout_windows_come_from_disjoint_time_segments` 断言 `max train end ≤ split ≤ min holdout start`）。
  - **种子控制**：`np.random.default_rng(seed)`，可复现且换种子确实改变抽样（`agent.md` §10）；`provenance` 记录 split 与每个抽中窗口，派生 MW 可逐条手算复现。
- 诚实边界（`agent.md` §4/§8，已在 trace `summary.json` 佐证）：trace 只提供**归一化形状**，`recovery_parameters_observed=false`、`deadline_available=false`、`continuous_power_available=false`、`calendar_dates_real=false`。因此：
  - 每个 MW 都是 **derived**：`demand = frozen_scale × mean(trace window)`，frozen_scale 是合成机制参数，不是实测功率；
  - 两 trace 来自不同集群、匿名相对时间，按**独立边缘分布**采样，不声称二者时序相关；
  - 场景概率是**蒙特卡洛采样权重**（对抽中窗口均匀），**不是**经验停电/失败概率；
  - 输出 `parameter_status` 恒携带 `TRACE_SCENARIO_PARAMETER_STATUS`（含 `derived`/`not_empirical`/`outage` 标记）+ 调用方状态，下游无法误当认证。
- 契约对接：生成的场景对齐 `EconomicScenario` 六字段并通过 H2 冻结校验器 `_validate_scenarios`（测试 `test_generated_scenarios_satisfy_the_downstream_holdout_contract`），可直接喂 `evaluate_economic_holdout`。
- 状态：本机已实现 + TDD。**已修**：`peak_normalized` holdout 泄漏（split-aware，见上），R3（`sol_reviewer`）PASS。**已接入 H2 正式入口**：`run_rq2_h2_stochastic_holdout.py` 增加 `scenario_source` 开关（`manual` 手工树默认 / `generated` 生成式），`generated` 模式经 `load_peak_normalized_shape_from_csv` 对**原始列**做 split-aware 重归一化（Google `measured_power_util_unweighted_mean`、Alibaba `requested_gpu_equivalents`），并把生成器诚实标签拼进 summary `parameter_status`、记录 `generator_provenance`；`load_trace_shape_from_csv` 对已按全窗峰值预归一化的列（如 Google `peak_normalized_unweighted_mean`）fail-closed 拒绝并给出改用原始列的重定向。runner 级回归覆盖诚实标签透传与 fail-closed 校验（`tests/test_rq2_h2_runner.py` 19 例，含 6 例生成式），生成器测试 + H2 holdout + frozen tree 及相关回归共 142 例全过（conda `compute` 环境），R3（`sol_reviewer`，含变异测试）PASS。**已完成**：① 经典场景缩减（fast-forward）作为第三种场景来源（[scenario_reduction.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/src/scenarios/scenario_reduction.py) `reduce_scenarios_fast_forward`，fast-forward 选择 + 最优 order-1 Kantorovich 再分配，代表点为输入子集、只重分配概率质量、透传诚实标签，测试 [test_scenario_reduction.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_scenario_reduction.py) 14 例含 1D order-1 手算 + 2D 欧氏默认度量数值 pin）；② 3-source H2 ablation 入口（[run_rq2_h2_scenario_source_ablation.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/experiments/run_rq2_h2_scenario_source_ablation.py) 读 [rq2_h2_scenario_source_ablation.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/rq2_h2_scenario_source_ablation.yaml)，固定同一 holdout、只变训练来源 manual/generated/reduced，CVaR 交叉校验为门、H2 稳健性逐臂报告不设门，`security_certified=false`，测试 [test_rq2_h2_scenario_source_ablation.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_rq2_h2_scenario_source_ablation.py) 15 例）。task#9/#10 已过 `sol_reviewer` R3 独立审查（2026-08-22 PASS，含独立数值复核 fast-forward 选择与 Kantorovich 距离）。**已完成**：③ 正式规模 config 与批处理驱动——3 份正式规模 base config（[rq2_l5_economic_stochastic_formal.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/rq2_l5_economic_stochastic_formal.yaml) 加密 13 点 λ；[rq2_h2_stochastic_holdout_generated_formal.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/rq2_h2_stochastic_holdout_generated_formal.yaml) n_train=200/n_holdout=60；[rq2_h2_scenario_source_ablation_formal.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/rq2_h2_scenario_source_ablation_formal.yaml) reduced target=50）+ 冻结批清单 [rq2_formal_batch.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/rq2_formal_batch.yaml)（19 job：核心 3 种子 + 机制邻域 grid/green/budget/β + L5 敏感性含故意 H3 失效点 budget=80）+ 批驱动 [run_rq2_formal_batch.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/experiments/run_rq2_formal_batch.py)（白名单标量覆写 + per-job 有效配置 SHA-256 + fail-closed + 复用各入口自有门，certifies nothing）+ 执行机入口 [run_experiment.ps1](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/scripts/run_experiment.ps1) 新增 `kind=rq2-formal-batch` 分支（产物重定向 `$runDir`）；测试 [test_rq2_formal_batch.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/tests/test_rq2_formal_batch.py) 12 例全过，本机全批端到端 19/19 job `gate_passed=true`、`batch_gate_passed=true`、`security_certified=false`（约 15 秒）。**待办**：④ 由执行机按 [RQ2_正式规模触发标签清单.md](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/docs/plan/RQ2_正式规模触发标签清单.md) 打 `run-*` 标签运行。
- **ablation 设计（回应"AI 买到了什么"）**：同一 L5 correct/B6 策略，分别在 (a) 手工冻结树、(b) 生成式 holdout、(c) 经典场景缩减 三种场景来源上执行 H2，报告 B6 场景外欠交付排序是否稳健，并检验生成式是否揭示手工树漏掉的尾部履约失败。

### 4.2 `grid_need` 物理内生化：A/B 增量

- 主口径 A：先固定正常态全数据中心负荷的最小成本 DC-OPF 调度，再对每个冻结 sustained N-1 状态在硬热限和 0.5·Pmax 合成纠正边界下最小化 Bus 8 数据中心削减；场景 `grid_need_mw` 取各状态最小削减的最大值。
- 对照口径 B：在同一 outage topology 上，以 Bus 8 削减、Bus 13 平衡的 PTDF 同时约束所有支路估算潮流并最小化所需削减。B 只作保守诊断，正削减结果显式标记 `direct_physical_dispatch_witness=false`，不替代 A 的硬约束可行性见证。
- 结构守卫：新入口拒绝配置中出现手填 `grid_need_mw`，固定排除 islanding branch 10，逐场景保存关键状态、支路、灵敏度、终止状态和完整 provenance；派生值进入既有 L5 后仍由 `c_grid >= grid_need` 硬约束承接，CVaR 不参与热限交易。
- 边界：当前仍是 selected-N-1 DC 与合成响应边界；缺少响应时标、full-N1、AC 电压/无功和工程设备参数，故所有输出恒 `security_certified=false`。本机已完成两线手算 pin 与 Bus 8 全 selected-state 单场景回归（A/B 均为 36.8 MW，关键状态均为 `branch_11_sustained`）；正式 A/B 批次未启动。已新增哈希绑定的 successor 清单 `configs/rq2_formal_batch_network_rts24_v2.yaml`，不改写原 19-job v1。
- R3 独立审查（2026-08-22）：`sol_reviewer` 最终 **PASS**；复核覆盖有限数值审计、B 的诊断/直接见证分离、v1 manifest schema 不漂移、successor 配置哈希及 RTS-24 数值 pin。

### 4.3 时序包络进入 L5 recourse

- 正确模型对 `chi[t]=c_grid[t]+c_green[t]` 建立唯一 `on/start/stop/recovery/debt` 状态，最大持续时间、最小事件间隔、事件次数、累计削减能量、恢复功率、恢复头寸、债务上限和完成期末债务均在优化内作为硬约束。
- B6 对网络与绿电服务分别建立两套同参数包络并各自使用完整 `D_flex`；求解后只把两者合计调用送回真实单包络，由物理评估器按最早可恢复规则重新调度唯一共享恢复功率，报告物理预算超额、恢复债务和违约。不得把求解器任选的双包络恢复轨迹相加后称为物理履约。
- 网络层只提供事故发生时的响应幅值。时序 runner 另用显式 `network_call_active[t]` 激活事件小时；当前配置中的事件位置、恢复头寸与包络参数均为合成敏感性，不是经验事故序列或合同能力。
- 本机 8 小时单事件机制算例：RTS-24 Bus 8 的 A/B 网络需求均为 `36.8 MW`；正确共享模型 provision `76.8 MW`，B6 provision `40 MW`，形成 `36.8 MW` 高估，且 B6 合计轨迹未通过真实单包络回放。该结果不是正式统计结论。
- R3 独立审查：最终 **PASS**；覆盖正常态逐时 OPF、事件激活、时序边界、确定性物理回放、配置 fail-closed、provenance 与终止状态语义。

### 4.4 Temporal H2固定策略holdout

- training端先独立完成correct/B6两套规划并冻结`D_flex`，之后才进入holdout；改变holdout轨迹不得改变已提交容量。
- holdout统一执行正确共享包络。服务欠交付通过`access_shortfall`报告；mandatory network call若违反MW、duration、event/rest、energy、recovery debt或terminal boundary，则独立记为hard temporal failure。
- solver unresolved不转译为失败。末端统计期未完成或允许事件延续的窗口标记right-censored，保留终端debt/state但不强制清零。
- 当前本机RTS-24 manual mechanism case：A/B下correct均提交`76.8 MW`、B6均提交`40 MW`；B6相对correct增加`36.8 MWh`期望服务缺口。50%窗口为right-censored，该比例不进入失败概率。此结果不是正式统计或经验概率。
- generated路径现从两个split-aware trace形状抽取完整连续小时窗口并追加合成恢复尾部；reduced路径在四个显式缩放分量的完整时序向量上执行fast-forward，只缩减training且保留输入代表轨迹。三来源消融只改变training，使用同一份生成后冻结并以SHA-256绑定的holdout。
- 首次本机RTS-24三来源机制配置全部correctness gate通过，但A/B下`h2_robust_across_sources=false`：阈值`1.0`的共享holdout未激活网络调用，manual策略在该holdout也没有B6额外欠交付，generated/reduced的correct与B6提交量约均为`12.3244 MW`。这是必须保留的失败区域，不能据此事后下调阈值制造阳性H2；该配置只证明管道闭环，不支持跨来源H2主张。
- R3独立审查：最终 **PASS**；新增连续trace、时序缩减与三来源消融的首轮REWORK四项均已闭环，复审确认period/terminal/recovery语义一致、training/holdout status分域、全请求arm可评估门和no-op计数正确。相关广泛回归135例、Ruff与manifest复核均通过。
- R4 successor：`RQ2_temporal_successor_preregistration.md` 与对应机器YAML冻结training-only q80/q90/q95/q99、3个种子、200/60场景、A/B及三来源的17-job矩阵；阈值`1.0`只作已观察边界复现。独立R4审查最终PASS；`formal_execution_ready=false`，未运行、未打标签，仍待用户单独授权执行。

## 5. 目标期刊评估：RQ2 单独发 TSG 是否够？

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
- 正式规模触发：批清单 [rq2_formal_batch.yaml](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/configs/rq2_formal_batch.yaml) + 批驱动 [run_rq2_formal_batch.py](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/experiments/run_rq2_formal_batch.py)；执行机打标签操作见 [RQ2_正式规模触发标签清单.md](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/docs/plan/RQ2_正式规模触发标签清单.md)，跨机闭环见 [科研实验闭环流程.md](file:///Users/bytedance/Workspace/Electricty-Grid/Electricity-Grid/docs/plan/科研实验闭环流程.md)。
- 论文产物：`paper/drafts`、`paper/figures`、`paper/tables`（当前为空，待 L5 结果固定后填充）。
