# RQ2 联合服务连续边界后继草案 v1

状态：`DRAFT_NONAUTHORITATIVE`  
日期：2026-09-12  
机器配置：`configs/rq2_joint_deliverability_boundary_successor_v1.DRAFT.yaml`

本草案记录 sealed v5 的时间边界诊断，以及用户本轮选择的“连续多日服务、跨日保留事件与恢复债务”后继方向。它不修改或替代 v5 科学协议、implementation v2 或 execution v3，不是 pre-seal/official review、执行许可、formal result 或论文证据，不能打开任何现有 gate。

## 1. 被审计的旧边界

sealed v5 对每个独立 24 小时 block 设初始 \(q=z=b=0\)，并在 hour 23 同时要求

\[
z_{23}=0,\qquad b_{23}=0.
\]

CFE arm 又要求 \(x^C_t=\tilde c_t(\alpha)\)，其中

\[
s^{RE}_t=1-d^{CFE,1}_t,\qquad
c_t(\alpha)=\frac{\max\{\alpha-s^{RE}_t,0\}}{\alpha},
\]

且原始请求不超过 \(10^{-6}\) 时才置为零。`cfe_only_shared` 的 \(q=x^C\)，`joint_correct_shared` 的 \(q=x^N+x^C\)，B6 的 CFE planning track 为 \(q^{cfe}=x^C\)。由于 \(q_t\le z_t\)，任一被纳入相应 track 的 hour-23 正有效 CFE 请求与旧 `z_23=0` 直接矛盾。该推论不依赖 solver，也不等于已经知道 grid/E0 条件下四臂正式状态。

## 2. 零 solver 必要条件审计

诊断只读取冻结的 pre-dispatch training marginals，并绑定下列输入：

- sealed v5 config SHA-256：`19d61a2913e346090db23d01de587b650d8599999c40a78a291f627915ec2a69`；outer SHA-256：`92a58498e1de5f84b132067e3d4a4443ae841747846785e9df54cd9afd7efdfd`；
- power manifest/hourly SHA-256：`28bc2c3c1ee3ba0ef6c940aec56f66d49587b5f2895d0e6b0b83fb0b6360cc63` / `b8b76fcfaa4dfbf63ff8c92092f357d43a7f21ffb51e76552593bb63f6a34ff1`；
- workload manifest/hourly SHA-256：`62f2ec5eefd0c651d8b970a16fce4fb6336ccb75ab09e3d2c67386cc26edb524` / `99da69e6a98ec45584339e57a37b3fbbf90d3d2d8f1e2c915229a1e4890faef3`。

冻结 training 包含 541 个 power blocks、34 个 workload blocks，因此每个 cell 有 18,394 个 raw marginal pairs。诊断从 sealed v5 展开 46 个注册 cells 和四臂 inventory，不根据结果增容、删 cell、改阈值或重选 support。

按 `c > 1e-6`，hour 23 正 CFE 请求的 power-block 数为：

| \(\alpha\) | 0.50 | 0.70 | 0.85 | 1.00 |
|---:|---:|---:|---:|---:|
| blocks | 358 | 478 | 541 | 541 |

因此在旧 24 小时完成期口径下，\(\alpha\in\{0.85,1.00\}\) 的每个 raw training pair 都触发 CFE track 的 terminal-inactivity 必要失败。若未来 finite/evaluable support 为空，estimand 仍是 undefined，而不是绕开该结论。

诊断还检查以下必要条件：逐时 available flexibility、总 energy、maximum duration、event-count 下界、总 recovery-energy 下界、causal prefix debt limit 和旧完成期的 causal terminal debt。event-count 下界使用

\[
\left\lceil\frac{\#\{t:\tilde q_t^{req}>0\}}{W}\right\rceil,
\]

允许一个 event 跨越零请求小时，避免把 positive-run 数误当 joint arm 的必要事件数。总恢复下界之外，causal debt 按每个 prefix 递推；未来恢复不能修复更早已经超过 \(\bar b\) 的 prefix。

available-flexibility 的 raw-pair 违反数如下；三列依次为 workload `flex_fraction` 0.05/0.20/0.50，同一 \(\alpha\) 的 OAT cells 共用该逐时容量必要条件：

| \(\alpha\) | 0.05 | 0.20 | 0.50 |
|---:|---:|---:|---:|
| 0.50 | 17,503 | 16,987 | 15,367 |
| 0.70 | 18,394 | 18,292 | 17,452 |
| 0.85 | 18,394 | 18,394 | 18,136 |
| 1.00 | 18,394 | 18,394 | 18,385 |

该表意味着删除旧 terminal contradiction 也不会自动产生可辨识前沿：例如 \(\alpha=0.85,f=0.20\) 的全部 raw pairs 已在逐时 CFE 投影上缺少可用柔性。它是含 CFE track 的充分失败见证；`network_only_shared` 仍因缺 `grid_need` 而不可评价。joint 网络请求只能使共享调用不减，因此 CFE 投影失败可继承；反向的“未触发”不能推出 joint/network 可行。

本诊断没有 dispatched grid、finite-support/E0 分类、完整 power-system feasibility 或 formal solver certificate。故 `full_physical_training_support_audited=false`、`E0_classification_available=false`，任何必要条件未触发都不表示 feasible。terminal-inactivity 与 causal-terminal-debt 标签严格属于 `legacy_sealed_v5_single_24h_completed_period`，不得用于宣称新的 continuous observation 在每个 hour 23 失败。

机器结果位于 `results/tables/rq2_joint_deliverability_boundary_diagnostic_v1_non_authoritative/`。其中 `summary.json` 和 `cells.json` 的 SHA-256 分别为 `7702f71e27fedb608940f28565b03f27b78d11e0ae834f7247b3ed0a5c896080` 与 `6f9bf70818d80872d3454da5e653c409273305b4165bef8f30f18941357a2db4`；summary 同时绑定本次 audit、boundary 和 runner 实现 hash，并明确 `solver_calls=0`。每个 cell 及其 CFE projection 也单独携带 legacy-v5 scope 和“不适用于 continuous draft terminal 判据”标签，避免脱离 summary 误读。

## 3. 连续多日主路径

用户于 2026-09-12 明确选择连续多日服务。每个 24 小时 block 只是 observation chunk，不是自动完成的 service/accounting period：

- hour 23 保留原始 grid/CFE 服务义务；边界不强制 inactive，不恢复、不清债；
- 下一 chunk 精确继承 `previous_call`、active 状态与持续时间、已观察 rest、event count、累计 call energy、recovery debt、`has_prior_event` 和 accounting-period ID；
- duration、minimum rest、event count、energy 和 debt 的约束跨 chunk 继续累计；没有注册的 period-change 依据时不得 reset；
- 当前组件只支持一个显式、fixed、nonrolling accounting period，并拒绝 period ID 变化。未来多 period 的预算定义与合法 reset 必须先形成新的注册合同和测试，不能从结果反推；
- `observation_end` 与 `service_deadline` 分开。缺未来观察使 completion 状态为 right-censored；缺已注册 deadline 则是 `blocked_missing_registered_completion_deadline` 合同缺失，而不是统计右删失。两者都不阻止传播已观察状态，也不抹去已经发生的 capacity、duration、energy 或 debt violation。

continuation 每一行都必须带实际的 grid/CFE obligation、workload 和 provenance；对该行采取的动作另须显式传入 `call_limit`、track-compatible `recovery_headroom` 与 `maximum_recovery_power`，不得用未证明的恢复头寸清债。边界链要求 split、arm/track、power trajectory/outage seed、workload trace/normalization hash 及 power/workload provenance hash 一致，且各 margin 内 `source_hour` 连续。跨 split、小时 gap、seed/trace 漂移或把不同事故世界拼接均拒绝。power 与 workload 可作为两个 margins 配对，但各自的连续轨迹身份必须保持。

仓库原始数据只证明一部分同 split 相邻 source hours 存在；workload v3 明确 `deadline_observed=false`、`checkpoint_observed=false`、`recoverability_observed=false`。因此不得合成零义务尾部、随意指定尾长、丢弃新 grid/CFE 请求或把观测末端当恢复完成。当前小组件仅证明状态和 provenance 边界可被执行、拒绝越界动作，并不是完整 formal planner 已修复。

## 4. 服务映射的科学边界

沿用的 additive mapping \(q=x^{grid}+x^{CFE}\) 是“分离义务进入同一柔性 ledger”的机制假设，用于检验共享事件/能量/恢复约束；本草案不声称它是唯一物理真值。同一物理削减是否可同时减少 CFE 缺口涉及政策结算与 co-benefit 定义，当前没有足够证据，保持 unresolved。不得在本草案内修改 sealed v5 的 shared budget 或据结果选择更有利的 fungibility 规则。

## 5. 可证伪后继与最小解卡顺序

1. 保留本次 46-cell/四臂审计作为 fixed diagnostic，不按阴性结果调参数；独立复核其 input/implementation/output hashes。
2. 对可用 source 输入做 continuation availability/provenance audit，明确可观察区间、事故 trajectory、workload trace、逐时新义务和 censoring；deadline/recoverability 没有来源时保持缺失。
3. 写一个完整、versioned 的 continuous scientific successor：定义 observation chunks、每笔或每期 deadline、accounting periods、合法 budget reset、holdout 边界和 estimand 在 censoring 下的含义。
4. 先用手算/合成轨迹证伪跨边界 duration、rest、event、energy、debt 和伪 recovery，再实现正式 planner；由 fresh independent R4 reviewer 审查后才能考虑 seal。
5. 只有新科学协议、数据门、实现/回归、独立 review 和单独 formal-run authority 都关闭后，才讨论 dispatched-grid/formal execution。V7 的 Windows/流程计算卡点不能替代本节科学边界的关闭。

可证伪主张是：在冻结的输入、连续状态和未来预先注册的 accounting/deadline 口径下，四臂是否存在完整 training support，以及 \(D_N,D_C,D_J,D_B\) 是否可定义并形成非退化 contrast。当前证据已经证伪“只要移除 hour-23 terminal condition 就会得到非退化前沿”，但尚未证伪或证实完整 continuous joint frontier。
