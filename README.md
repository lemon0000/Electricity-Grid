# Electricity-Grid

*Last updated: 2026-09-02*

Research code for staged data-center interconnection and grid expansion.

Current machine responsibilities, evidence status and the next gated action are
summarized in
[`RQ2_开发机任务与执行边界.md`](docs/plan/RQ2_开发机任务与执行边界.md).

当前 Vnext two-block evidence runner 为 isolated v8
`NONFORMAL_COMMITTED_SUCCESS / POST_RESULT_INDEPENDENT_REVIEW_PASS`。外置 pre-run execution-review receipt
SHA-256 为 `04cd6b421ebeef07e00c1d8ab08bb15d721110ff454c32e7898eca2eff6b486e`；独立 post-result PASS
已物化为外部 machine receipt，SHA-256 为
`28e546b8f5f3bc8c8402c86ec723ec9e35da041ba74676c9adb59cd338980ca6`，其中明确
`cryptographic_reviewer_signature_present=false`。唯一一次 fixed 0008→0009
运行使用 session `9d16ff4da3bab583876d6fbf5d09c0dde4bc5b3bc57334b891cfe38038044f62`，两个 fresh worker
PID/create-time 分别为 `30404/13432731802848210300` 与 `8600/13432731839688457900`，0009 的 predecessor
精确等于 0008 record digest。public-only readback 将 publication 分类为 `committed_success`：result/PUBLISHED
typed-tree file SHA-256 分别为 `03528f052f127d819dc07edff860efd7652e5b28da34cfac6be245ba0e75331c`、
`f01ec3391a20d692aa8974c08da8f1af81dd4b79a07e1aff9cb0290fea4f8920`；Lamport attestation payload/signature
SHA-256 分别为 `158b14130823a80acfa643c2df7ab7611ad518ed7c1647864501c3ab719eecda`、
`0a595309844822ba529db6e1a5c7d8ddf2f47ef60fc7a130dd8014e01b347c7f`。0008/0009 resource journals 均为
`child_exited`、sample/expected=`6/6` 与 `39/39`、exact 5 s gaps、0 lateness、authority mapping match；两者实际
HiGHS runtime 均为 1.15.1/4 threads。fresh/raw-consumed seed 均不存在，只保留 SHA-256
`8e5f25e1b8a3aecb4d2a32a2a6d55aea65ca178425e6d47e9cf9fec35d378aa2` 的不可复用无 seed tombstone。
block-zero formal activation successor v1 的独立 review 为 `REWORK`：后台 controller 在 Popen 后没有 exact
PID/create-time 与 authority-accepted handshake，immediate exit 仍可能被报告为 spawned。machine REWORK receipt
SHA-256 为 `bb398d74c67fdfce41d7fcc64e58820a5f8ad6f16d3ba1ff5c9e1a7d529b6a14`；v1 outer
`b492e4babe182d38ad6be865df424d1cce59cef57c2c6a85b896cffddfad0b87` 及全部 v1 bytes 保持不变。

successor v2 的独立 R4 verdict 为 `ESCALATE`。machine receipt
`configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v2.json` 绑定 v2 outer
`8c5db5e265141378b537e9e3096198c0f86221a324423a646d6645d107b56764`，并明确无 reviewer cryptographic
signature、不得授权 execution。四项 finding 是 reviewer PASS 与 user run authority 未分离、实际 project-code import
closure 未由 frozen expected hashes 封口、release 后失败仍可能被误写成 `launch_incomplete/formal_started=false`，以及缺少
四阶段真实 E2E/失败矩阵。

successor v3 的独立 R4 verdict 为 `ESCALATE`。receipt
`configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v3.json` 绑定 v3 outer
`087127892db1a55955ddc87b2491520a61a9b19d6d7f0e56040ce0c9d980ee3b`，明确来自独立 review report 的转录、没有
cryptographic reviewer signature，也不含 execution authority。V3 的 50-file closure 完整性陈述不成立：`ast.ImportFrom`
没有实现 `node.level`/package 语义，漏掉 `ac_validation`、`network_grid_need`、`scopf`、`service_risk`、`osqp_qp`
等实际 local imports；其 bootstrap 也在 release acceptance/spawn receipt 后停止监督，无法覆盖完整 block 生命周期和
post-acceptance abrupt exit。因此 v3 只作为已失败历史版本保留，不能生成 PASS 或启动 formal。

V4 versioned candidate 维持两个 fixed-path 串联门：review PASS 仍只能把 review 置 true且保持
`formal_execution_authorized=false`；另一个当前 absent 的 explicit user formal-run authority 必须绑定 exact v4 outer、
review、formal-v5 config、controller command、77-file execution closure 与 fresh lease。production closure 按 Python
relative-import/package/namespace/submodule 语义递归解析，三处 computed dynamic import 由 sealed authority-key→module
mapping 明确冻结；独立 stdlib `modulefinder` bytecode oracle 与 production AST discoverer 得到 exact 同集。每个 execution
boundary 都比较 manifest 的 frozen expected SHA-256。独立 V4 review 对该 77-file closure 与 oracle 未发现新 blocker，
因此 V3 的 closure finding 在 V4 已闭合。

V4 对 post-release lifecycle 的完成性陈述已被独立 R4 review 推翻。bootstrap 首个 startup `try` 在 stable persist release
并等待 acceptance 后仍只 `except Exception`，所以 `KeyboardInterrupt`/`SystemExit` 可留下
`release_persisted=true/post_release_unresolved=false` 且 child 仍存活。terminal-success writer 只预查 unresolved，而
unresolved writer 不反查 terminal；per-file hard-link 只能防止单文件覆盖，不能阻止同一 attempt 同时存在 terminal success
与 unresolved。focused tests也没有覆盖这两个窗口。因此 V4 post-release/dual-terminal 同一验收项再次失败。

v3 closure/inner/outer SHA-256 为
`cdc272b2f98d637c4ed020d4303c35ba29ed3e5c3c38994ece722509751f44e2`、
`cf05fcf2c05a42b4b5cfb36c535fd7b54fc2dac69f2ebbbdc76f220f42971f51`、
`087127892db1a55955ddc87b2491520a61a9b19d6d7f0e56040ce0c9d980ee3b`。focused `10 passed`；related raw
`91 passed, 3 failed`，3 项均为 sealed V8 已执行后的失效 absent-state 断言，current-state 为
`91 passed, 3 deselected`。扩展 transport broad 首轮 `137 passed, 2 failed, 3 deselected`，两项 live preloader 在当时
available commit 未达到冻结 10 GiB 时正确 fail closed；不把它们改写成实现或科学失败，精确 deselect 后为
`137 passed, 5 deselected`。Ruff 与两个 validate-only 入口通过，后者机械报告 1071 blocks、HiGHS 1.15.1/4 threads、
0 solver/0 formal-root writes。negative execute 首先因 user formal-run authority absent 拒绝，lease hash 前后不变，
consumed/audit/formal roots absent。V3/V4 以上账目都是历史实现验证，不是独立 PASS。V4 independent verdict 为
`ESCALATE`，receipt
`configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v4.json` SHA-256 为
`1d4f5f1b65512a0092438051055171c5abf4dbbe2aa358675c5f580636bc4e9c`，绑定 V4 outer
`6936d06a5bc8d191f5eaf235fe7784c36193ac6343d88d16cbbd3e5bea8d2068`，无 cryptographic reviewer signature、无
execution authority。V4 不得创建 PASS 或运行；当前没有可启动 formal candidate。下一步必须由用户明确授权新的
versioned successor（V5）；此前 V4 design authorization 既不是 V5 design authority，也不是 formal-run authority。

V4 config/closure/formal config/contract/controller/bootstrap/test/inner/outer SHA-256 为
`78167060bcb456ff88124e8b8d628db5aeb2d2f8a17ad77643dfb381fd666431`、
`ba9195283cf3ad149e08c875820198648d0a9c0cf6b99ac7e3c37b212683b948`、
`935b430c3151dcaf3802d13259f8c9930d53c130f13a836d4fa737b1074f6f0c`、
`8bb9fe840fc9a1ba8a6e3188240f42e1c3198436c4bb54395115af0a6d0f7583`、
`4360ba651f1ae085f12ac21aab562d1e0138eca177085eb4e714e9e01b3a073a`、
`9c3c8033377bc0539bcdfabdd93f4f3f15206123983e27abff9d7da38b534ca1`、
`4c1007e88d7459621316b8f43c16cd943b48fbe000385c3358e5fc1dc9122022`、
`89d465c31a963d87cc8173314941045b23798b51595b899ed8a1540890217588`、
`6936d06a5bc8d191f5eaf235fe7784c36193ac6343d88d16cbbd3e5bea8d2068`。V3 red regression 精确复现
五个漏项；V4 focused `15 passed`、V1–V4 `43 passed`。related raw `106 passed, 3 failed` 与 transport broad raw
`154 passed, 3 failed` 的三项均为 sealed V8 已运行后失效的 absent-state 断言；精确 deselect 后分别为
`106 passed, 3 deselected` 与 `154 passed, 3 deselected`。本次两项 live preloader 均通过，因此没有沿用旧的
resource-dependent deselect。Ruff、AST、bootstrap/controller validate-only通过；negative execute 先因 explicit user
formal-run authority absent 拒绝。

完整账目按实际时间顺序为：writer raw `479 passed, 13 failed`；writer first 13-deselect
`478 passed, 1 failed, 13 deselected`（V4 fast 是唯一红点）；writer isolated V4 `1 passed`；writer second
same command `479 passed, 13 deselected`；reviewer same command `478 passed, 1 failed, 13 deselected`；
reviewer isolated V4 连续两次失败，且 exact argv/stdout/journal/state/returncode 缺失；current 14-deselect
`478 passed, 14 deselected in 348.20s`。不修改 V4 的外部只读 runtime instrumentation 本次得到
`child_exited`、sample/expected `1/1`、returncode 0，未复现失败；journal SHA-256 为
`0d62844b8e02f763018b85ea200c168492bd8526fe6042a9016a7c845dfb1555`，非权威证据文件 SHA-256 为
`e2138fd2038a6d330149e05e01507618f646bd5a9c5f4d60e026507242f16111`。该证据不建立失败根因，也不是
V8 finding；V4 保持 sealed/superseded。V7/V8 fast probes 与全部 66 个 V8 tests 仍在 current-state broad 中保留。

## 论文主线聚焦（RQ2）

毕业论文/期刊投稿的主线聚焦 **RQ2：网络安全与小时级CFE共同约束下的业务柔性
可交付前沿与不足归因**。确认性设计比较
`network-only / CFE-only / joint-correct / joint-B6`，以
`I_joint = D_J - max(D_N,D_C)`为主容量指标，并分解
`I_joint = I_sep + A_B6`。B6用于量化分离时序记账相对correct造成的有符号容量
偏差，并在共享物理包络中评估冻结策略后果。科学协议见
[联合服务可交付前沿确认性方案v2](docs/plan/RQ2_联合服务可交付前沿确认性方案_v2.md)；
[v1科学基础](docs/plan/RQ2_联合服务可交付前沿确认性方案_v1.md)保持不可变。

本 README 其余部分描述的是**更广的项目全景与共享基础设施**（L0-M6、B0-B5 基线、
RTS-GMLC 选择性 N-1 基准、AC 复算与 repair 认证链）。这些不是需要删除的"旧目标"：
RQ2 的 B6 错误基线与共享预算复用 `deterministic_fx` / 随机基线脚手架，B2-B5 也是 RQ2
叙事的对照基线，RQ1 多阶段自适应作为后续扩展保留其脚手架。论文只是从全景中**收窄主线**，
而非替换代码树。范围与创新定位的权威来源仍是 `agent.md`（§4 已将 RQ2 定为首篇主创新），
数学规格见 `docs/model_spec/formulation.md`。

Current scope includes the reproducible grid-security foundation, deterministic
quarterly fixed-POI expansion, B0-B5 synthetic planning mechanisms and
fixed-policy holdout, the F1-F3 duration/recovery mechanism gate, and the M6
chronological input/dispatch interface. Named six-hour and full-day native
RTS-GMLC selected-N-1 day-ahead DC-SCUC benchmarks, a six-candidate common-state
POI scan, and two-representative direct-AC plus zero-data-center control and
recovery diagnostics are coupled end to end. The 24-hour and multi-POI software
gates are closed, but the AC treatment-follow-up gate remains blocked by two
zero-data-center hours without a feasibility witness under the official voltage
limits. The latest `repair_005` formal attempt published four of six required candidate
checkpoints, then stopped during candidate 5 cost normalization. Its
operational-interruption artifact records that the registered PID is no longer
running, the active lease is retained as stale evidence, and no terminal
failure, frontier, or joint-AC result was observed. This is not mathematical
infeasibility or a formal solver failure, and the attempt must not be resumed.
A fresh successor attempt must build the six-budget-candidate AC-aware
commitment frontier plus its frozen parent baseline; joint AC remains locked
until that frontier, all manifests, both stage certificates, primary regret, and
the final 24-state audit are complete and verified. Observed
absolute power, flexibility and recovery evidence, same-clock
incidents, full N-1, engineering AC security, and formal annual/hourly CFE
conclusions remain unimplemented or externally blocked.

The RQ2 confirmatory successor studies the joint temporal deliverability
frontier across four registered hourly-CFE targets. Four matched arms estimate
the limiting single-service requirement, signed joint interaction,
separate-envelope interaction, and B6 capacity bias. Public-marginal
transport bounds remain the robustness layer for fixed-policy holdout outcomes.
E0 grid states retain their unconditional mass and remain outside conditional
service-risk metrics. The development host is blocked from formal execution.
See `docs/plan/RQ2_联合服务可交付前沿确认性方案_v1.md` for the prospective
design and `docs/plan/RQ2_开发机任务与执行边界.md` for current execution gates.

### RQ2 execution status

The fresh four-run HiGHS/Gurobi confirmatory pilot completed successfully.
The process-isolated HiGHS V8 run also completed the fixed nonformal
`0008 -> 0009` sequence and passed independent post-result review. Formal
activation successors V1-V4 did not obtain execution authority; V4 ended in
`ESCALATE`, so no formal candidate is currently executable.

The joint-deliverability preregistration amendment v2 is sealed for independent
R4 review (`outer SHA-256 ae1e8a8a5c4c276e5c0d54900636de94e5402f29923817cf8cb70067b90c90f7`).
Its 46-cell implementation and formal execution remain blocked; sealed v1 is
the immutable scientific predecessor.

The branch-head automation default remains `pytest-smoke`. The 1071-block grid,
pairwise and identification stages remain closed. A future formal activation
successor requires its own draft, seal, independent review and explicit
formal-run authority.

## L0: RTS-24 DC-OPF and N-1

The current implementation loads PYPOWER's `case24_ieee_rts`, builds an
independent Pyomo quadratic DC-OPF, and solves it with HiGHS. It then enumerates
every active single-branch outage. Each connected island receives its own angle
reference when intentional islanding is explicitly enabled, and native system
load cannot be shed. Unplanned islanding is rejected by default.

The L0 contingency screen uses `RATE_A` in every state and permits independent
corrective redispatch within generator minimum and maximum output. RTS-24 does
not provide a corrective-response envelope in this data source, so L0 is kept
only as an optimistic upper-bound diagnostic.

## M1: evidence-aware security audit

M1 retains all three RTS ratings: `RATE_A` for normal and sustained states,
`RATE_C` for the immediate post-contingency screen, and `RATE_B` without using
it until a duration mapping is documented. The joint preventive-corrective
SCOPF contains 107 modeled states: one base state, 37 fixed-dispatch immediate
branch states, 37 bounded-redispatch sustained branch states, and 32 sustained
generator-outage states. Branch 10 (7-8) is an unresolved unplanned-islanding
contingency and is reported as an excluded failure, not counted in those 107
states.

The RTS case has no 10- or 30-minute generator ramp data. M1 therefore reports
predefined redispatch sensitivities from 0% to 100% of `Pmax`; every row is
marked `synthetic_sensitivity_not_for_certification`. These runs measure model
sensitivity and must not be described as an operational security certificate.
Generator immediate-frequency response and full chronological load/renewable
conditions remain outside this peak-snapshot RTS-24 audit.

The joint DC sensitivity is infeasible at 0% and 5% of `Pmax`, then feasible at
10%, 20%, 50%, and 100%, with exact recalculated base costs of 76414.42,
67630.81, 61001.24, and 61001.24. Full-state AC restoration checks both the 10%
and 50% cases. After provisional benchmark remedies, 104/107 states pass at
10% (generator outages 22, 23, and 32 still fail) and 107/107 modeled states
pass at 50%.

The remedies are candidates, not installed assets: raise surviving branch 9 to
about 255 MVA after branch 4 fails; apply a +140 MVAr change at bus 6 after
branch 9 fails (from `BS=-100 MVAr` to net `+40 MVAr`); and open branch 6 after
branch 26 fails. The response envelope is still synthetic, branch 10 remains
unresolved, and these remedies lack project evidence. Therefore
`security_certified` remains `false`.

## RTS-GMLC load proxy

The official RTS-GMLC `v0.2.3` data are pinned at commit
`3ece0d3725c844056132393ee252b3083dd4eab4` and verified by SHA256 manifest.
The source contains 73 buses, 158 generators, 120 AC branches, and 8784
continuous day-ahead hours. Area 1 load is used only as a same-lineage RTS-24
load-shape proxy; RTS-GMLC generator ramps must not be copied into PYPOWER
RTS-24 because the unit sets are not identical.

Four observed load snapshots use the lower order statistic. A fixed-online
model fails at the 858.81 MW minimum because all positive-capacity units have a
combined `Pmin` of 1036 MW; 1416 of 8784 hours lie below that threshold. The
audit now applies the same single-snapshot static unit-selection model to all
four conditions. With a synthetic 50%-of-`Pmax` redispatch bound, all four
snapshots solve all 107 modeled states without load shedding, committing 11,
11, 24, and 23 real-power units from minimum through maximum load.

This is not chronological SCUC. The four commitments are independent; startup
cost, minimum up/down time, and intertemporal ramps are not modeled. The cost
MILP uses a 65-breakpoint tangent approximation and reports an exact polynomial
recalculation only at the selected solution.

Commitment-aware AC restoration now scales each bus's P/Q demand at constant
power factor, keeps the reactive-only synchronous condenser available, turns
off unselected real-power units, and deterministically reassigns the REF bus.
All four base snapshots restore to AC-secure points, with losses of 27.68,
42.12, 66.08, and 47.13 MW. Contingency-state AC restoration has not been run
for these load snapshots, and renewable trajectories remain absent. Every row
therefore retains `security_certified=false`.

## Native RTS-GMLC selected-N-1 benchmarks

The primary formal result
`rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1` couples all 24 continuous
hours of the Google day-0 no-flexibility business input to the native 73-bus
RTS-GMLC network. It covers `2020-01-01 00:00-23:00 UTC`, with 158 generators,
120 AC branches, one controllable lossless DC branch, and a data-center demand
range of `172.770833333333-189.729166666667 MW`.

This is a day-ahead DC-SCUC benchmark with 12 preregistered states per hour,
including normal. The selected security set covers branches `A12-1`, `B22`,
`C6`, and `CA-1`, plus generators `121_NUCLEAR_1`, `213_CC_3`, and
`313_CC_1`; islanding branches `B11` and `C11` are explicitly excluded. Three
constraint-generation iterations leave seven states in the final active master,
while all 12 preregistered states are checked before the fixed-commitment
all-state ED. The prescreen objective is `1168052.6505076461 USD`; the ED upper
bound is `1193156.5322057535 USD`, and the valid active-master lower bound is
`1193155.3829459916 USD`. Their certified absolute gap is
`1.1492597619 USD` (`9.632095e-7` relative), within the configured tolerance.
The largest independently recomputed, unrounded residual is approximately
`1.4835e-9`. The SHA-256 of its `SHA256SUMS` manifest is
`61b9d8c127354375769b5c1cf9e45e4340eafb0e89d8b07acbd8a08c9e1a0399`.

The companion regression result
`rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1` covers
`2020-01-01 00:00-05:00 UTC`. Its selected branches are `A27`, `B22`, `C6`,
and `CB-1`, with the same three selected generators. Two constraint-generation
iterations and the all-state ED give `157084.446540127 USD`; the certified
absolute gap is `1e-9 USD` (reported relative gap zero), and all reported
residual maxima are zero. Its manifest SHA-256 is
`405c5109ef405f1961f6e9e461be5bfa42bd88f074bd30fa49e67006f6edcd10`.

The 24-hour scaling fix removes the pointwise custom commitment-symmetry order:
that order deleted valid crossing multi-period unit trajectories. A valid
reserve-up/commitment convex-hull envelope supplies the needed lower-bound
strengthening without changing the integer feasible set. The focused SCUC test
module reports `10 passed`; the completed repository-wide regression at that
stage reports `386 passed`. The current eight-module zero-control, 560, 565,
IPOPT, and serialization regression reports `62 passed`.
Full-repository Ruff and scoped Black checks also pass.

Both named downstream results set
`chronological_dispatch_request_built=true` and
`chronological_grid_dispatch_coupled=true` only within their named horizons.
They remain `derived_benchmark` results, not full M6 readiness or certification.
The source business artifact scales normalized utilization by an assumed 250 MW
reference; it does not supply observed absolute MW. All flexibility and recovery
fields are zero, so neither result supplies real flexibility, recovery, or VMA
evidence. The incident chronology is empty, which does not establish that no
incidents were observed, and the initial state is optimization-derived from a
free boundary rather than an observed chronology. These are selected-N-1 rather
than full-N-1 results, day-ahead rather than real-time SCED, and DC rather than
AC security. They are not site, contract, engineering, or capacity
certification; `absolute_power_mw_available`, `flexibility_observed`,
`full_m6_model_input_ready`, `security_certified`, and
`formal_vma_published` all remain `false`.

Reproduce the two formal results from the repository root with:

```powershell
conda activate compute
python -m experiments.run_rts_gmlc_day0_scuc --config configs/rts_gmlc_google_day0_scuc.yaml
python -m experiments.run_rts_gmlc_day0_scuc --config configs/rts_gmlc_google_day0_full24h_scuc.yaml
```

The frozen output directories are
`results/tables/rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1/` and
`results/tables/rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1/`.
Each contains nine payload files plus `SHA256SUMS`, which pins all nine:

```text
generator_dispatch.csv
hourly_dispatch.csv
incident_chronology.csv
initial_state.csv
normal_branch_flows.csv
security_audit.csv
security_branch_flows.csv
security_generator_dispatch.csv
summary.json
SHA256SUMS
```

## AC-aware commitment V3 formal solve

The previous V2 run was stopped after about `46725 s` without a candidate
checkpoint, frontier, joint-AC call, or usable progress log. That operational
termination is not infeasibility evidence and V2 must not be resumed. Its
termination manifest SHA-256 is
`e8bcef7466a1dfa44e4c0a444eb297fbf7160cf1f7596485c86a6fd9984b799b`.

Gurobi 13.0.2, CPLEX 22.2.0.1, and Xpress 9.9.1 are installed and pass native
and Pyomo smoke tests, but their currently available automatic licenses cannot
fit the formal `215689`-variable, `350615`-constraint proxy model. HiGHS 1.15.1
is the only solver that passes the current formal capacity gate. A frozen
six-hour, 24-state benchmark repeated 1/4/8-thread configurations twice and
mechanically selected four threads without reading objective values. The
benchmark result manifest SHA-256 is
`4b05c7d7fcbd8f64ddb9eb61d4ee15c571a7905d8ebd453ac19d07cbf56c63d1`.

A second frozen pilot compared the full-state monolith with exact selected-state
constraint generation. Exact CG passed both repetitions, including final
24-state fixed-shared LP and residual audits, in `54.057 s` and `54.502 s`.
Both monolith repetitions hit their limit with a certified interval width of
`0.003796157` and were ineligible. The formal V3 method is therefore HiGHS with
four threads and exact CG. Its preregistration manifest SHA-256 is
`01646721d15395668bf0079cb6fe218dc0625187d1fbf108c5db74e47ae33f88`, and its
input-contract SHA-256 is
`af4a388d80c211611a8e1dad3861936decb7f3c3e2de3a422116c87c013d8aa0`.

This is the fastest eligible configuration in the preregistered comparison,
not a claim of universal runtime optimality. The first formal proxy master found
its incumbent at `2801.9 s` and closed zero gap about five seconds later. The
frozen parent baseline was already a strong feasible point with proxy
`0.24328147100424327`, but the current Pyomo `highs` interface is not warm-start
capable and V3 does not pass a MIP start. This affects runtime, not correctness.
A successor may benchmark `appsi_highs` or native `Highs.setSolution`, but only
under a new implementation hash and preregistration after start mapping,
acceptance logs, repeated runtime, final bounds, and residuals are verified.

Each proxy-maximization and cost-minimization stage restarts from the same seed,
screens every inactive state after every master, conservatively promotes an
unresolved screen, and requires a final full 24-state audit. The run computes
the actual `LB`, `UB`, absolute gap, and incumbent-relative gap from the current
feasible and dual bounds. The target relative gap is `1e-4`; the preregistered
maximum accepted relative gap is `1e-3`, and the proxy stage also has a `1e-3`
absolute-gap cap. These thresholds are frozen: only the measured interval is
dynamic, so no post-result tolerance tuning is permitted.

Formal eligibility uses the stage-level incumbent-relative `target_attained`,
`eligibility_status`, and `maximum_acceptance` fields. The nested
`certificate.relative_gap` and `certificate.target_gap_attained` use a generic
solver diagnostic scale and are not V3 eligibility fields. The final
cost-normalized commitment must also pass a primary-proxy regret audit: regret
may not exceed either the stage-one absolute gap plus `1e-7 + 1e-6`, or the
hard maximum `0.0010011`.

Historical V3 attempt `formal_20260719T061959Z` is no longer running and must
not be resumed. It did not publish all six budget checkpoints or the complete
frontier and is not evidence of mathematical infeasibility. The immutable
repair-002 preregistration has been published, and no solver process is
currently running. After its independent review passes, candidate generation
must start as a new V4 successor attempt. Joint AC remains forbidden until that
attempt has atomically published and verified all six budget checkpoints, the
complete frontier including the frozen parent baseline, manifests, both stage
certificates, primary regret, and the final 24-state audit.

## RTS-GMLC multi-POI and direct AC replay

The frozen multi-POI design mechanically selects buses `108/120`, `208/220`,
and `308/320` as one 138 kV and one 230 kV load bus per area. Bus 108 is a
previously seen anchor, so this is not a six-candidate blind experiment. A
normal-state prescreen was used only to form the common selected-N-1 set; all
full comparisons use the same ten branches (`A11`, `A12-1`, `A34`, `B12-1`,
`B22`, `B6`, `C12-1`, `C27`, `C6`, and `CA-1`) and three generator outages
(`121_NUCLEAR_1`, `213_CC_3`, and `313_CC_1`), giving 24 states per hour. The
common-security contract SHA-256 is
`7865c7544817acd2d0dd6a461766862af52f7175eb24f2c1466f52e70115aa87`.

Four candidates are feasible in the frozen DC model. Their certified lower and
upper bounds in USD are `120: 1207456.214789805/1207456.214789805`,
`108: 1212140.771918603/1212140.772348714`,
`220: 1207773.41079156/1207773.41079156`, and
`320: 1207594.61558767/1207595.022772649`. Bus 120 is therefore the only
certificate-separated lowest-cost feasible candidate. Buses 208 and 308 are
model-infeasible after adding `branch_B12-1_immediate` and
`branch_C12-1_immediate`, respectively, even in the free-boundary continuous
commitment LP relaxation. This proves infeasibility only for the frozen common
selected-state model; it is not an engineering site rejection. The mixed
outcome aggregate manifest SHA-256 is
`85f157a5f14f73ffa851c8dc1bc263f67719d794a900101b987dcab3f21dac66`.

The AC replay covers buses 120 and 108 over all `24 hours x 24 states` at unity
and 0.95 lagging power factor, for 2304 cases. It maps saved DC generation and
commitment directly into the public RTS-GMLC AC case, reconstructs fixed
lossless DC1 endpoint injections, and performs no Q-limit switching, active
redispatch, restoration, or added POI transformer/line/compensation. Source MW
branch ratings are used only as MVA proxies. The frozen AC input contract
SHA-256 is
`7dc28350aaa137a3f99a90a83365ebafb58c8de739a2999a5a93ed4ea0babd41`.

The first complete batch was invalidated after a PYPOWER audit showed that
generator sorting could make a colocated unit other than the reported unit
absorb slack power. It is retained only as a diagnostic under manifest
`51ba90b32ca7702d92b49fa70832a56160b41ad9ee286990d2d937142ee9e05e`.
Amendment 003 requires a reference bus with exactly one online committable
generator and mechanically reproduces the original failure before applying the
fix. Its implementation SHA-256 is
`6a9f2050a7882ef4c7fae72daefbc018d966ad46977bed22748383f15fe26ac0`.

Amendment 004 then found a second implementation issue: a colocated online
Q-inert generator could overwrite the source `VG` of the unique Q-capable
controller during PYPOWER bus-voltage initialization. It changes only that
initialization rule and invalidates the amendment-003 outcome batch under
manifest
`2b5b705d2074ddb8f846b7a8d897ed87d32021446fd867825b7dd3a0982e2a7e`;
the former `2276/2304` counts are retained only as a transparent parent
diagnostic.

The amendment-004 result reports all 2304 cases: 2296 converge, eight do not,
and zero are direct-secure. Of the converged cases, 2296 violate voltage limits,
2217 violate a reactive-power bound, 717 violate a branch rating, and 1470
violate an active-power bound; these categories overlap and exclude the eight
non-converged cases. The maximum DC1 reconstruction residual remains `3e-9 MW`,
and all converged cases pass the non-slack-PG audit. Its result manifest SHA-256
is `ee4894bba4e65433ffed4b31e4d96c78035bd2413dd4fa6accb3eb9f16c0609a`.

The preregistered zero-data-center normal-state control converges in all 24
hours but is secure in none: all 24 hours violate voltage and Q criteria, 11
also violate a branch rating, and 10 violate an active-power bound. It is a
reoptimized operational counterfactual, not a matched treatment control, but it
shows that the direct-replay failures cannot be causally assigned to the data
center or POI from these batches alone.

Bounded AC-OPF recovery under the official `0.95-1.05 p.u.` voltage limits next
finds 11/24 witnesses in the reference-provider mode and 22/24 in the common
distributed-committable mode with PYPOWER algorithm 560. Algorithm 565 reaches
the same 22/24 set; both miss hours 15 and 21. An independent CasADi 3.7.2/IPOPT
stack also finds 22/24 witnesses from each of three fixed initializations and
returns `Infeasible_Problem_Detected` at the same two hours. These local solver
outcomes do not prove global infeasibility. Symmetrically expanding both voltage
bounds by `0.01 p.u.` produces 24/24 witnesses but reaches `VM=1.06000001 p.u.`,
outside the official `VMAX=1.05`; it is sensitivity evidence only and cannot
replace the official envelope.

The canonical IPOPT table is
`rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic_v2`. It deterministically
removes one duplicated `solver_objective_mw2` CSV field from the superseded v1
serialization, makes zero solver calls, and changes no scientific outcome. Its
preregistration and result manifest SHA-256 values are
`ffdf5d5df29101b463438cbf753e6b80b6babd31d74ea72df82c9648cf236ab3`
and `75d40ffe53ded9747f916d57a3d00921d5087549afc8148cb2953f5924bf7332`.

The first AC-aware commitment preregistration (`v1`) froze input contract
`2892a459137998fe7825acafc2391d9367f9cbfb66dcaeb2dc5c06f0a49237e8`, but a
real 24-hour pre-solver check then found that its core incorrectly treated
hourly `BUS_TYPE` as a cross-hour static field. The candidate invocation was
stopped before any frontier artifact was published and before any joint AC
solver call. The v1 preregistration is therefore invalidated, not overwritten;
its invalidation manifest is
`7ac6a6a2ecc76304376654b36d6a0e83e5bd506e9f3ff537356fa13ad94ac3dd`.
The v2 amendment changed only that validation rule, while requiring each hour
to use legal `PQ/PV/REF` types with exactly one `REF`. The corrected real-input
preflight covered 24 hours, 73 committable units and 72 reserve providers with
zero IPOPT calls. Its formal process was operator-terminated after about
`46725 s` without a checkpoint, frontier, or joint-AC call. That termination is
not infeasibility evidence; V2 is closed and must not be resumed. The V3 method,
provenance, error contract, and historical attempt are documented in the
dedicated section above.

The current machine status remains `treatment_followup_gate_passed=false`,
`ac_security=false`, `security_certified=false`,
`full_m6_model_input_ready=false`, and `formal_vma_published=false`. The current
valid step is to pass independent review of the immutable repair-002
preregistration and create a new V4 successor attempt. That attempt must publish
and verify all six budget checkpoints, the complete frontier including the
frozen parent baseline, manifests, both stage certificates, primary regret, and
the final 24-state audit before joint AC may run under the frozen protocol. The
independent alternative is to obtain sourced tap, switchable-shunt,
compensation, and controller parameters. Until then, treatment runs and
paper-result freezing remain stopped.

## Empirical workload and power traces

The repository now has two source-locked production datasets. Google PowerData
2019 contributes 55 normalized PDU traces linkable to ClusterData, two
power-only MVPP traces, and 96,616 machine-to-PDU mappings (508,896 five-minute
rows in total). Only 24 rows carry the bad-measurement flag, but 116,517 rows
(22.896%) carry the bad-production-power flag; source completeness therefore
does not imply that every production estimate is usable. Alibaba PAI GPU v2020
contributes the 145.6 MiB `stage1_core` job, task, group-tag, and
machine-specification subset. Both sources are CC BY 4.0 and have local SHA-256
manifests and validation summaries.

Google power is normalized utilization rather than MW. A guarded BigQuery
acquisition now pairs cell `f` / `pdu17` day 0 with ClusterData CPU usage,
priority, and machine events. The three successful jobs processed
551,002,439,062 bytes and billed 551,004,667,904 bytes (`0.501 TiB`) under the
frozen `1 TiB` gate; two failed attempts report no processed or billed byte
value. Resume paths validate the original Job parameters as well as SQL,
schema, source snapshots, and billing caps. Alibaba gives observed AI job
intervals and requested resources but no continuous power, checkpoint
progress, deadlines, or recovery parameters.
Its dates, months, and years are anonymized; only relative intervals, time of
day, and day of week are preserved. The datasets describe different systems
and must not be joined as one observed chronology. They support source-tiered
trace-driven benchmarks, not site, contract, or engineering certification.

The source-specific processing layer is now reproducible and hash locked.
Google produces a 744-hour normalized shape from 55 workload-linkable PDU
domains after filtering `bad_measurement_data`; no PDU values are summed or
imputed. A separate day-0 product uses the documented 600-second clock offset
to pair 24 hourly `pdu17` measured-power values with NCU-usage bounds and 168
hour/priority rows. Priorities 0-119 are only a low-priority usage candidate
proxy, not observed flexibility; ambiguous and unknown priorities are not
reassigned. Alibaba produces complete job/task tables, a strict 732,318-task
positive-GPU request cohort, a 1,642-hour relative-arrival table, and a full
quality/join audit. The Alibaba and Google clocks remain separate and are
never treated as an observed join.

The project also pins the CC BY 4.0 supplementary data from Mukherjee et al.
(2018), DOI `10.1016/j.dib.2018.06.067`: 1,534 source rows representing
state-level major-outage reports from 2000 through July 2016. The rows span 50
postal jurisdictions (49 states plus DC); the source includes AK and HI and has
no RI, so it is not summarized here as either 50 states or strictly the
continental United States. Reported fields include event times, duration,
cause, demand loss, and customers affected, subject to documented missingness.
Candidate identity, duplicate aggregation, duration, missingness, and loss
cohorts are preregistered in `us_major_power_outages_candidate_cohorts_v1`.
The primary sustained-duration cohort has 1,385 candidate groups representing
1,398 source rows. Candidate groups are still not established independent
physical incidents, so they cannot estimate incident frequency or an
unconditional duration distribution. They do not identify branches or
generators, cannot be mapped to RTS components, and are not on the data-center
workload clock.

## M2: deterministic fixed-POI expansion MVP

M2 exhaustively enumerates `no_start` and every fixed start-quarter candidate.
For each candidate, it sends the original convex quadratic objective to OSQP,
audits the unscaled constraints, and uses HiGHS for linear feasibility repair.
The best repaired candidate is selected only after all `K+1` candidates have
been resolved. This finite enumeration no longer requires a PWL dispatch
selection or an MIQP solver, but without an explicit optimality-gap certificate
it is reported as a numerical QP result rather than a mathematically exact
global optimum. The bundled existing-corridor project still has one start
decision, one common lead time and one total investment cost; commissioning can
increase both the fixed POI limit and the `RATE_A`/`RATE_C` limits of named
existing branches. It does not create a new circuit or change branch reactance.
Native system load has no shedding variable, and every MW connected at the POI
is firm load in all selected security states.

The frozen RTS-24 benchmark is explicitly synthetic, not site or engineering
evidence. It places the POI at bus 8 and bundles thermal uprating of branches 11
(8-9) and 12 (8-10). With a two-quarter lead time, the project starts in `q1`,
commissions in `q3`, and produces a connected-demand path of
`50/50/200/250 MW`; the `q2` access shortfall is `50 MW`. All 107 modeled states
in each quarter, 428 state-quarters in total, satisfy the audited DC balance,
thermal, outage and corrective-response constraints. Branch 10 remains an
excluded unplanned-islanding failure.

The complete numerical run resolves all five fixed-start candidates and selects
`start_q1` at `501360875.14` synthetic objective units. The next candidate is
separated by `74933666.62`, while the largest candidate-level numerical repair
acceptance envelope is `11.04`. All repaired candidates have original-model
constraint violation at most `8.11e-7`; the selected 428 state-quarter audit has
maximum balance residual `6.27e-8`. The repair envelope combines absolute,
relative, and objective-scaled feasibility tolerances. It is not an optimality
gap or error certificate, and none of these synthetic values is site evidence.

M2 deliberately identifies connected capacity with requested firm demand that
is actually operating, so it cannot yet represent unused contract rights or be
used directly for unused-MW-year and F/X metrics. Cost inputs use synthetic
objective units without a calibrated currency year. The 50%-of-`Pmax`
corrective bound is also synthetic, generators are fixed online, and expansion
AC validation is not run because MVA and reactive engineering parameters do not
exist. Consequently `security_certified` remains `false`.

## M3: fixed-policy F/X mechanism and chronology sensitivity

M3 separates contract capacity `C=F+X` from actual connected demand. It
evaluates an explicitly fixed quarterly F/X and project-start policy rather
than optimizing the split: no evidenced firm/X price differential, capacity
holding cost, or contingency frequency exists yet, so direct optimization
would be non-identified. Normal and branch-immediate states prohibit X calls;
sustained branch and generator states may call only active X. Firm breach and
post-call conditional breach remain hard-disabled.

Each quarter has two independent DC security layers. The actual layer serves
`Dconn=min(Dreq,C)` and can call at most the active conditional demand. The
contract layer is a counterfactual dispatch under the same external load,
equipment and outage state: it serves full `C` in normal/immediate states and
at least `F` after a sustained X call. It is not a transition guarantee from
the actual dispatch. A second solve minimizes required calls only to choose a
canonical feasibility certificate; its sum across mutually exclusive states
and both layers is not an operational power requirement, MWh, expected events,
or cost. The primary fixed-policy dispatch now sends the original convex
quadratic objective directly to OSQP, audits the unscaled constraints, and
uses a HiGHS L1 linear feasibility projection before minimum-call
normalization. It no longer relies on a piecewise-linear cost selection, but it
is reported as a direct numerical QP result rather than a mathematically exact
global optimum. The movement and objective-deviation envelopes only govern
numerical feasibility acceptance; neither is an optimality gap or error
certificate.

The frozen synthetic policy is `F/X = 50/0, 50/0, 175/75, 175/75 MW`. All 856
state-layer-quarter rows (`4 quarters x 2 layers x 107 states`) pass balance,
thermal, outage, service-floor, call-limit and corrective-response audits. At
`q4`, actual demand is 125 MW and requires no call, while the independent
contract layer still validates `C=250 MW` and may call up to `X=75 MW` in
sustained states. The generator audit contains 28,248 raw rows.

The static DC gate now assigns zero chronological validation hours, so it does
not release T milestones from a declared repeated condition. A separate
8784-hour chronology audit checks one explicit full-X call witness with hard
duration, event, energy, response, recovery-power, debt, and terminal-debt
limits. It uses the RTS-GMLC calendar but does not use its load values as a
data-center workload. The flat full-contract counterfactual has no recovery
headroom at 250 MW, so temporally qualified capacity is `50/50/175/175 MW`:
`T_module=T20=q1`, `T50=q3`, and `T100=q4+` (right-censored). This is a
mechanism counterexample, not event-frequency evidence or chronological grid
security certification. For this RTS-24 M3 artifact, generator frequency
response, branch 10, expansion AC parameters, and chronological unit commitment
remain blocked; therefore `security_certified=false`.

## M4: deterministic B0-B2 baseline gate

M4 compares `B0_WAIT`, `B1_FIRM`, and `B2_STATIC_FX` under the same frozen
quarterly demand path `D = 50/100/200/250 MW`, fixed POI/project data, and
107-state security set. Planning variables are indexed only by quarter/root,
with no state or scenario index. The lexicographic rule first minimizes physical
access shortfall `U`, then reports both the minimum- and maximum-X-exposure
endpoints on that primary-optimal face. The displayed plan is the minimum-X
endpoint for conservative normalization; it is not an economic optimum.

The formal synthetic results are `U=327600 MWh` for B0 and `U=109200 MWh` for
both B1 and B2. B2's admissible X-exposure interval is `[0, 549600] MWh`: its
displayed minimum-X endpoint has `X=0` in every quarter, while its maximum-X
endpoint follows `X = 50/50/75/75 MW`. Static F/X therefore does not improve
physical access shortfall over firm-only B1 in this frozen case, and the unique
F/X split remains economically non-identified without evidenced relative-value
inputs.

Each policy completes 10 reported stages, then sends its fixed displayed plan
through M3's two-layer audit: 428 actual states plus 428 contract-counterfactual
states. All four milestone labels are right-censored for all three policies,
`T_module=T20=T50=T100=q4+`, because the static baseline declares zero
continuous validation hours; these are not certified milestone achievements.

Implementation exposed a numerical failure in exact-fix dispatch repair even
though the underlying plan was feasible. The final M3 closure therefore uses
an L1 linear feasibility projection and audits the original constraints,
variable movement, and objective deviation against declared numerical
acceptance envelopes. The movement and objective-deviation envelopes are not
an optimality gap or error certificate. These results remain synthetic,
non-engineering evidence and retain `security_certified=false`.

## M5a: frozen B3-B5 scenario-structure gate

The auditable input in `configs/rts24_stochastic_baselines.yaml` freezes a
four-quarter, 12-leaf progressive factorial tree. Six common-q1 demand paths
use only the M4 milestones: `50/50/100/200`, `50/50/100/250`,
`50/100/200/200`, `50/100/200/250`, `50/200/200/200`, and
`50/200/200/250 MW`. They are crossed with the existing two-quarter project
lead time plus either zero or one extra quarter. Current demand class is
revealed before q2 decisions, the exogenous delivery regime before q3, and the
terminal 200/250 MW demand before q4. Each q2 class therefore retains two
future demand paths instead of revealing the full trajectory. B3 keeps all
leaves in one planning decision group for the full horizon, B4 refines through
`1/3/6/12` groups, and B5 intentionally separates all leaves from q1 with
machine-readable `implementable=false` as a perfect-information bound.

The six demand-path weights of `1/6`, project-state weights of `1/2`, and leaf
weights of `1/12` are a balanced synthetic mechanism design, not empirical
ramp-up or delay probabilities. The delivery state represents an observable
external approval, supply-chain, or delivery environment; it is not evidence
of project-specific construction progress. Planning decision groups constrain
only controllable `F/X/z_start`; scenario-dependent project availability is
derived from the shared start plan and each natural history rather than being
forced equal across on-time and delayed leaves.

The M5a config also pins the complete shared-input signature schema
`rts24_common_fair_inputs_v2` and SHA-256
`76cda29db68705cc3f2ef5025f32d30ef07ceea62a552a97c45b01bf83287794`.
Validation rebuilds this signature from the live M4 config and RTS-24 security
states, so drift in quarter hours, load multiplier, POI, project, service
envelope, contingency set, redispatch, objective, or solver closes the gate.
This gate therefore cannot support a formal VMA, economic optimum, engineering
recommendation, or security certificate.

The stochastic model must restore `Dconn=min(Dreq,C)` so a root policy can hold
contract rights not yet used in a low-demand leaf. Its physical lexicographic
rule first minimizes expected access shortfall, then reports the min/max total
contract-capacity exposure. On the minimum-total-capacity face it reports the
min/max X exposure before applying any non-economic project normalization.
This avoids arbitrary capacity paths when real capacity values and opportunity
costs are unavailable.

## M5b: B3-B5 stochastic mechanism gate

The B3, B4, and B5 models now embed both actual service and the full-contract
counterfactual over the same 107 security states. B3 and B4 reuse one network
feasibility copy per natural history (`1+3+6+12=22`) while retaining their
different planning decision groups. B5 is exactly separable by leaf because
all of its planning decisions have perfect information; the implementation
solves the 12 independent leaf models and probability-weights their complete
lexicographic faces. A synthetic two-line case verifies that this decomposition
matches the monolithic B5 formulation.

The frozen RTS-24 run passed all 13 stages for every policy and the required
ordering `U_B5 <= U_B4 <= U_B3`:

| Policy | Implementable | Expected access shortfall U (MWh) | Total-contract exposure E_C (MWh) | X exposure on minimum-E_C face (MWh) |
|---|---:|---:|---:|---:|
| B3 | yes | 403200 | [880800, 880800] | [0, 494400] |
| B4 | yes | 274400 | [954400, 1101600] | [0, 522000] |
| B5 | no | 274400 | [954400, 1101600] | [0, 522000] |

B4 reduces the in-tree synthetic shortfall by `128800 MWh` relative to B3 and
matches the B5 perfect-information bound on this particular frozen tree. This
is an in-sample mechanism result, not a formal VMA: the next gate must execute
the fixed B3/B4 policies on independently frozen out-of-sample paths without
future-information reoptimization. Probabilities remain synthetic and all
outputs retain `security_certified=false`.

## M5c: fixed-policy synthetic holdout gate

The deterministic holdout in `configs/rts24_stochastic_holdout.yaml` freezes
six monotone demand paths that do not occur in the training tree and crosses
them with both supported project-delivery states. Before q2, q3, and q4
decisions, the mapper uses only current q2 demand, realized project delay, and
current terminal demand, respectively. The frozen M5b summary and endpoint CSV
are SHA-256 pinned. B5 is rejected as nonimplementable, and neither F/X nor the
project-start plan can be reoptimized on a holdout path.

Both minimum-X and maximum-X policies on the minimum-total-contract face were
executed. All `2 policies x 2 endpoints x 12 leaves = 48` executions passed
M3's 107-state actual and contract-counterfactual audit. The two X endpoints
produce the same access-shortfall result:

| Policy | Synthetic holdout expected access shortfall (MWh) |
|---|---:|
| B3 | 474780 |
| B4 | 364380 |

The resulting set-valued holdout adaptivity interval collapses to
`[110400, 110400] MWh`. The benefit is not uniform: B4 is better on all six
on-time leaves, equal on the three delayed/upper leaves, and worse by
`22080-33120 MWh` on the three delayed/lower leaves. Thus the evidence supports
a conditional adaptivity claim rather than universal dominance. These are
balanced deterministic holdout weights, not empirical probabilities, so the
artifact labels this a synthetic holdout adaptivity value and retains
`formal_vma_published=false` and `security_certified=false`.

## M6a: F1-F3 temporal-flexibility mechanism gate

`configs/rts24_flexibility_envelope.yaml` SHA-256 pins the M3 state table and
separates two traces. `network_minimum_call_replay` derives its call magnitude
from the maximum minimum-call certificate across the 107 bounded security
states in each quarter and layer. That replay is degenerate: all frozen M3
minimum calls are `0 MW`. It therefore passes F1-F3 but does not establish the
value of temporal flexibility or chronological grid security.

`full_x_contract_stress` applies the same one-hour full-X stress under three
nested envelopes:

- F1 checks only the active/contract X MW limit.
- F2 adds response, ramp, duration, rest, event count, and energy limits.
- F3 additionally requires bounded recovery power/debt and terminal repayment.

F1 and F2 retain `250 MW` in q3/q4 and reach T100 in q3. F3 fails despite the
same MW trace: the actual q3 event leaves `75 MWh` of debt, while the contract
counterfactual reaches `150 MWh` after q4 because the flat full-contract
baseline has no recovery headroom. F3 therefore qualifies only `175 MW` in
q3/q4 and leaves T100 right-censored at `q4+`. This is a synthetic counterexample
to MW-only certification, not evidence for event frequency or a real contract.

The replay uses network-derived call magnitudes but does not rerun hourly grid
dispatch. Full M6 certification remains blocked by observed data-center
absolute MW, flexibility/recovery headroom, observed same-clock event
timing/frequency, a complete evidence-window coupled run, full N-1, and
engineering-grade AC security. This
specific F1-F3 replay artifact keeps
`chronological_grid_dispatch_coupled=false` and `security_certified=false`; the
separate named RTS-GMLC six-hour and 24-hour results described above do not
retroactively change those artifact-local flags.

The repository now fail-closes the external-data boundary before any full-M6
runner is allowed. `src/evaluation/chronology_inputs.py` validates exact,
source-locked business and incident chronologies, including continuous
offset-aware timestamps and explicit frequency semantics. Security-state
enumeration is rejected as event frequency. `src/grid/chronological_dispatch.py`
defines a full-horizon SCUC/SCED result contract and audits service balance,
recovery headroom, load shedding, generation balance, availability, and declared
normal/N-1 security. A dispatch backend can now pass its actual recovery schedule
into the flexibility evaluator instead of having it silently replaced by greedy
post-processing. The typed builder binds sourced recoverable workload to the
contract call limit and both physical and connected-capacity recovery headroom;
named incidents must appear in the checked security-state IDs. Linked windows
also carry debt, active-event duration, rest, event counts, and energy, while
terminal debt is enforced only at real period boundaries. This closes the
internal interface gap only; it does not change
the two certification flags above. The exact contract is documented in
`docs/model_spec/m6_chronological_data_contract.md`.

## Environment

```powershell
conda activate compute
python -m pip install -r requirements.txt
```

NumPy is pinned to 1.26.4 because PYPOWER 5.1.19 calls APIs removed in NumPy 2.

## Verification and experiment

```powershell
conda activate compute
python -m pytest
python -m experiments.run_rts24_base --config configs/rts24_base.yaml
python -m experiments.run_rts24_security --config configs/rts24_security.yaml
python -m experiments.run_rts24_scopf --config configs/rts24_scopf.yaml
python -m experiments.run_rts24_deterministic_expansion --config configs/rts24_deterministic_expansion.yaml
python -m experiments.run_rts24_deterministic_fx --config configs/rts24_deterministic_fx.yaml
python -m experiments.run_rts24_fx_chronology --config configs/rts24_deterministic_fx.yaml
python -m experiments.run_rts24_deterministic_baselines --config configs/rts24_deterministic_baselines.yaml
python -m experiments.run_rts24_stochastic_baselines --config configs/rts24_stochastic_baselines.yaml
python -m experiments.run_rts24_stochastic_holdout --config configs/rts24_stochastic_holdout.yaml
python -m experiments.run_rts24_flexibility_envelope --config configs/rts24_flexibility_envelope.yaml
python -m experiments.validate_rts_gmlc_data --config configs/rts_gmlc.yaml
python -m experiments.validate_google_power_data --config configs/google_power_2019.yaml
python -m experiments.validate_alibaba_gpu_2020_data --config configs/alibaba_gpu_2020.yaml
python -m experiments.validate_us_major_power_outages_data --config configs/us_major_power_outages.yaml
python -m experiments.process_google_power_data --config configs/google_power_2019.yaml
python -m experiments.process_google_power_workload_day0 --config configs/google_power_workload_day0.yaml
python -m experiments.process_alibaba_gpu_2020_data --config configs/alibaba_gpu_2020.yaml
python -m experiments.process_us_major_power_outages_data --config configs/us_major_power_outages.yaml
python -m experiments.build_m6_google_power_shape_benchmark --config configs/m6_google_power_shape_benchmark.yaml
python -m experiments.build_m6_google_power_workload_day0_benchmark --config configs/m6_google_power_workload_day0_benchmark.yaml
python -m experiments.run_rts24_load_conditions --config configs/rts_gmlc.yaml
python -m experiments.run_rts_gmlc_day0_scuc --config configs/rts_gmlc_google_day0_scuc.yaml
python -m experiments.run_rts_gmlc_day0_scuc --config configs/rts_gmlc_google_day0_full24h_scuc.yaml
python -m experiments.handle_rts_gmlc_multi_poi_outcomes --stage finalize
python -m experiments.run_rts_gmlc_multi_poi_ac_replay_slack_amended --stage run
```

The experiments write dispatch, branch flows, security sensitivities,
deterministic expansion state audits, AC validation, load-condition
commitments, B0-B2 and B3-B5 endpoint audits, and machine-readable summaries
to `results/tables/`.

The repository exposes two Google-derived business artifacts. The 744-hour shape
artifact maps an ex-post whole-window peak-normalized fixed replay to an assumed
250 MW project peak. The paired 24-hour day-0 artifact instead maps
`measured_power_util_mean` directly to an assumed 250 MW reference capacity,
without day-0 peak renormalization; its demand range is
`172.770833333333-189.729166666667 MW`. Priority and NCU fields are retained only
in `candidate_proxy_audit.csv` and never populate M6 flexibility fields.

Both standalone artifacts pass `m6_business_chronology_v1` only as
no-flexibility `derived_benchmark` inputs: flexible demand, recoverable demand,
and recovery headroom are zero. They do not themselves provide observed
absolute MW, observed flexibility, incidents, or a grid solve, so their own
summaries retain `chronological_dispatch_request_built=false` and
`chronological_grid_dispatch_coupled=false`. The named downstream RTS-GMLC
solves consume either the first six rows or the complete 24-hour day-0 window
and set those two flags to `true` only in their respective results. Across the
inputs and downstream results,
`absolute_power_mw_available=false`, `flexibility_observed=false`,
`full_m6_model_input_ready=false`, `security_certified=false`, and
`formal_vma_published=false` remain mandatory.
