# D 有限阶段方案比较有界开发诊断合同

2026-11-03，`DRAFT_NONAUTHORITATIVE`。按 `agent.md` §7、§9 起草，承接[论文骨架与 D 配置](thesis_outline_and_d_config_20261103.md)第 7–11 节。本文档是**执行前的登记草案**，不是运行授权；启动前须完成 §9 整体性能审查并取得登记确认。

D 的目标只有一个：对同一批给定计划与情景，产出**三种评价方法各自的定值**与**其安排在实际路径完整时序约束下的重放定值**，形成判断差异矩阵。D 不产生最优解、不做投资优化、不做 AC 认证、不消费 F 链工件。

---

## 1. 既有接口与骨架复用

D 不新建设计语言，绑定以下既有实现：

| 用途 | 既有实现 | 状态 |
|---|---|---|
| 三方法枚举 | `src/staged_deliverability_development_v1.py` `METHODS = ("instantaneous","fixed_headroom","full_temporal")` | 已有 |
| 逐小时动作与违约 | 同文件 `advance()`、`execute()`、`assessment()` | 已有 |
| 12 个分类槽位 | `src/staged_deliverability_evaluation_records_v1.py` `development_design()`：`business_progress × grid_progress × method` | **已预留，未绑定** |
| 两个定值字段 | 同上 `method_conditions_satisfied`、`full_replay_conditions_satisfied`（当前均为 `None`，`status="planned_schema_only"`） | **已预留，未绑定** |
| 网络层与 F/X 分层 | `src/staged_network_development_v1.py`：`execute_network()`、`contract_checks()`、`NetworkState` | 已有 |
| 终结/保存/重开 | B3 链 `staged_termination_development_v1.py` 及 `staged_deliverability_b3_v1_non_authoritative` | 已有，本轮不复用其 attempt |

`development_design()` 的 `comparison_slots` 是 2 业务进度 × 2 电网进度 × 3 方法 = 12 槽。D 的网格（6 计划—情景单元 × 3 方法 = 18 次评估）与之不同：**12 槽是分类骨架，18 是评估次数**，二者不是同一计数，报告须分别标明，不得混用。本合同的网格见 §4。

## 2. 必须先建的能力：动作序列可重放

这是 D 相对 B1/B2/B3 的唯一新增能力，也是全包风险最高处。

现状（实测读码）：

- `advance()` 的 docstring 明写 `approximate methods retain diagnostic, not physical, plans`；
- `committed` 仅在 `state.method == "full_temporal"` 且存在 blocking 违约时置 False，近似方法的动作无条件记账；
- `instantaneous` 分支的 `room = min(capacity, workload*flexible_fraction, workload)`，**绕过** `max_duration`、`minimum_rest`、`max_events`、`max_call_energy`、`max_debt`、`call_ramp` 全部事件包络；
- `fixed_headroom` 的恢复上限用常数 `p.fixed_headroom`，**替代**实际可用恢复资源 `min(fixed_headroom, ledger.debt/eta)` 与设备/供电/清洁余量。

因此：近似方法产出的是一份"其自身信息集下认为合理"的动作轨迹，但该轨迹从未在完整物理约束下执行过。要求：

1. 新增动作轨迹抽取：对每个 `(plan, scenario, method, hour)` 输出显式 `(q, r)` 二元组序列，附该小时的信息集标识与输入 SHA。
2. 新增 `replay_full_temporal(params, observations, actions)`：把 `(q, r)` 序列作为**给定命令**逐小时送入完整时序物理（不做内部重规划），记录该命令在 `full_temporal` 约束下的违约码、已记账债务、期限结局。
3. 重放必须使用**同一** `observations`、同一 `params`、同一窗口；不得重算动作、不得修正动作、不得跳过违约小时。
4. 三方法的动作轨迹、重放轨迹与两套定值分别保存，任一为空即该槽 `未决`。

动作外置是**新增实现**，属 `agent.md` §7 的 R3 类（涉及恢复语义、事件包络与非预见性），须 `sol_reviewer` 独立审查。它不改动 `advance()` 既有的 `full_temporal` 语义——只新增一条读取给定动作的执行路径。

## 3. 定值规则（与 `agent.md` §4 三值判据一致）

对每个 `(计划, 情景, 方法)`：

- `method_conditions_satisfied`：沿用 `assessment()` 的既有返回。`instantaneous` 只检查 `instant_codes`；`fixed_headroom` 剔除恢复小时的 `{device_capacity, scalar_supply, hourly_cfe}`；`full_temporal` 检查全部。返回 `None` 表示未决（覆盖不完整或右删失）。
- `full_replay_conditions_satisfied`：取 §2 重放结果，判据同 `full_temporal`，但**只报告**，不参与方法自身定值。
- 两值组合映射为标签：

标签词汇由两条轴共用，但两轴分布须分别报告，不得合并：

| 方法定值 | 参照方定值 | 标签 | 含义 |
|---|---|---|---|
| True | True | `D3_agree_pass` | 简化评价足够成立的范围 |
| True | False | `D1_false_pass` | **惯例会放过会违约的计划** |
| False | True | `D2_false_reject` | 过度保守，损失可接入容量 |
| False | False | `D4_agree_fail` | 一致失败 |
| 任一为 None | — | `D5_undetermined` | 单列，**不计入 D1–D4** |

- **轴一（`label`）**：参照方为方法自身安排在完整时序约束下的重放定值。
- **轴二（`strategy_label`）**：参照方为完整时序策略对同一计划的定值。

**D2 在当前方法集下结构上不可达**：两种简化均放宽约束而非收紧（`instantaneous` 省略事件包络，`fixed_headroom` 以常数替代实际恢复余量），不可能比完整时序评价更保守。该性质已由测试 `test_approximations_are_structurally_permissive` 固定；引入收紧型简化时该测试须失败。C3 仅主张 D1 方向，D3/D4/D5 计数仍须完整披露。

`full_temporal` 在轴一上的两值理论上恒等（同一物理，动作重放回自身），差异只可能来自覆盖不完整；若出现非平凡不等，属实现缺陷，须停止该包并作为 finding 登记，不得计入结果。

## 4. 网格

| 维度 | 水平 | 依据 |
|---|---|---|
| POI | 1（复用 B2/B3 的固定两母线） | 既有配置，不新增 |
| 给定计划 | 2：电网按期 / 电网延期（`grid.delays` 的两个键） | 与介绍稿第 6 节"业务快慢达产×电网按期或延期"一致；构造，声明的情景假设 |
| 业务进度 | 2：快 / 慢 达产 | 与 `development_design()` 一致 |
| 设备路径 | 单独给定，三态 | B1 状态机 |
| 窗口 | 16 小时，含 2 次阶段切换、已登记期限与必要后续观察 | 由 B1 的 10 小时扩展，理由见骨架 §7 |

主网格 = 3 × 2 = **6 单元**；每单元 3 方法 × 2 定值 = 6 次评估 → **36 次评估**（主网格）。

恢复时段匹配臂（对应骨架 6.2）：6 单元 × 3 个到达时段 × 2 定值 = **36 次评估**。匹配约束：固定即时网侧与 CFE 请求、已兑现延期、恢复起点债务、清洁额度总量与峰值，只改到达时段。

敏感性（最小集）：`f ∈ {5%, 20%, 50%}`、设备余量 K 两水平、`alpha` 三水平；只跑标签判定，不做全量重放。

主网格 + 匹配臂 = 72 次评估；敏感性约其 1/3。**三者分别报告，不相加为独立样本量。**

## 5. 数据与情景来源分层

- 网络、设备、任务、清洁额度：**构造/合成**，逐项标注。不得写成实测。
- RTS-24 若接入，仅作公共网络换代检查，不改主网格的构造属性。
- 跨源配对（工作负载 / 可再生 / 网络）明确标为构造情景，不解释为同址同钟观测。
- 每个单元的 `business_input_sha256`、`shared_exogenous_input_sha256`、`equipment_plan_sha256`、`grid_plan_sha256`、`policy_sha256` 按 `development_design()` 既有字段填入，缺一即该单元无效。

## 6. 成本登记（草案，待 §9 审查确认）

按 B1 3.007s / 180 步、B2 12.327s / 362 点、B3 15.321s / 599 点外推：每 16 小时单元约 580 PYPOWER 点；36 × 580 ≈ 21k 点；按 B3 每点 25–40 ms 计，主网格 PYPOWER 时间 9–14 分钟；加审计与持久化，主网格 wall 0.5–1.5 小时。匹配臂同量级，敏感性约 1/3。

**登记上限：总 wall ≤ 4 小时；单进程 RSS ≤ 512 MiB；全部产物 ≤ 32 MiB；并发 = 1（无 child 时）；零 solver 调用、零外部下载、零付费查询。**

三项不确定性必须带进 §9：

1. 16 小时窗口可能触发 B3 已登记的 O(T²) 状态摘要编码访问，B3 的 T≤10 外推不成立；
2. 若主网格改用 RTS-24，逐点成本高于两母线，须重新估；
3. 敏感性分支若复用主网格判定，会引入依赖耦合，须在登记时固定复用关系。

## 7. 停止与失败处置

- 任一单元出现求解未决或数值异常 → 记 `D5`，单列，**不重跑追平**。
- wall / RAM / 存储触及登记上限 → 停止，保留已接受单元，不延期续跑。
- `full_temporal` 出现非平凡两值不等 → 停止该包，作为实现 finding 登记，不产出结果。
- 所有 attempt 保留原字节；失败不删除、不覆盖、不重试同一路径。
- 单个单元失败不阻断其余单元，但须在报告中逐单元列明成败。

## 8. 跑之前固定的可证伪判据

| 判据 | 内容 | 不满足时 |
|---|---|---|
| P1 网格完整性 | 6 单元 × 3 方法 × 2 定值全部报告，含 D3/D4/D5 占比 | 停止，不进入 6.3 写作 |
| P2 差异存在性 | **至少 1 个单元**出现 `D1_false_pass` 或 `D2_false_reject`，且该单元的期限或恢复事件可逐小时解释 | C3 按既有收缩条件降级为描述性 |
| P3 匹配有效性 | 6.2 的对照确实固定了请求 / 已兑现延期 / 起点债务 / 总量与峰值 | 该臂结果不进入 C2 |
| P4 一致性 | `full_temporal` 两值恒等；D3+D4+D5 全部报告不得省略 | 任一不满足即为实现缺陷 |

P2 的"至少 1 个单元"是固定绝对阈值，**不得**在看到结果后调整，也不得改用"显著"一类措辞。

## 9. 启动前必须完成

1. 本合同的整体性能审查（`agent.md` §9 全部六项），特别是 §6 三项不确定性的实测覆盖。
2. §2 的动作外置与 `replay_full_temporal` 的 R3 独立审查材料准备。
3. 网格覆盖性核对：确认网格落在恢复额度到达窗口卡期限与 K 余量接近业务占用的临界侧（骨架 §7），而非均匀网格。
4. 目标目录登记：`results/tables/staged_deliverability_d_v1_non_authoritative/attempt_NN/`，独占创建。

## 10. 与既有门禁的关系

- D 不改动任何冻结协议、配置、hash、receipt、manifest 或既有结果。
- D 不消费 F 链 `saved_fresh` 工件；若需 F 级复现证据，走独立后继。
- 产出命名**禁用** `formal`、`certified`、`published`、`production`；全部字段保持 `DRAFT_NONAUTHORITATIVE`。
- `resource_admission`、`formal_preregistration`、`formal_result` 恒为 `false`。
- `security_certified=false` 与 `aggregate_contract_release=false` 继续成立；D 的结论限于声明的 DC 模型与故障集合。

## 11. 交付物

1. `report.json`：36 + 36 次评估的逐单元定值、标签、违约码、SHA 绑定。
2. 差异矩阵表：6 单元 × 3 方法的 D1–D5 分布，附 D3/D4/D5 占比。
3. 动作轨迹与重放轨迹的配对样本（至少覆盖每个标签一次）。
4. `validation_report.md`：成本实测、失败与未决清单、与 §8 判据的逐条对照。
5. 供骨架 6.3 直接引用的表格草稿（不进论文正文，只作数据源）。
