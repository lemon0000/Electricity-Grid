# H1 generation 值域投影 successor v2

## 授权与范围

用户在 2026-09-30 明确授权本 R4 规则的开发、测试与独立审查：将 `generation ∈ [-1e-9,0)` 映射为正 `0.0`，原始 witness 与转换差值保留，对 candidate 重验全部约束、功率平衡、原目标 hex、strict locks 与 chronology，任一失败仍拒绝。新 native 运行需要新的可审查封存包与独立运行授权。

v1 单小时校准在 index 25 的 `commitment/201_CT_1` 阶段因 `generation[normal,0,201_CT_2]=-2.6987936877750535e-12` 不满足严格非负 carry 值域而拒绝。该历史拒绝符合 v1 合同，保持不变。v2 是新的科学规则与计算身份，不能回写 v1 的状态、projection 或 claim。

## 确定性规则

1. canonical raw decode、输入/模型/solver/provenance 绑定、`verify_numerical` 与既有 native numeric predicate 必须先通过。原 residual/integrality `1e-9`、native gap `1e-8`、精确目标 hex 比较及 prior lock 等式保持原值。
2. 从当前 canonical H1 model 枚举 `generation['normal',0,uid]` 的精确变量名。只对这些变量且 `-1e-9 <= raw < 0` 映射为正 `0.0`。阈值事前固定、不可由调用者提供；`-0.0`、零、正数及其他变量保留原 hex。
3. raw H1 audit 可仅因既有 `unit_chronology: generation_mw must be a finite nonnegative number` 拒绝；任何其他 raw audit error 继续拒绝。原 objective hex 必须与 raw provenance 一致。
4. candidate 必须通过既有完整 H1 assignment audit，包括变量界、fixed 值、全部约束、整数性、锁与 chronology。独立记录 canonical `power_balance` 等式的最大残差并检查 `<=1e-9`，所有锁残差也检查 `<=1e-9`。candidate 的 canonical objective hex 必须与原始 provenance **完全相等**。
5. 任一检查失败，阶段拒绝，锁不推进，无 projection。若当前目标是被转换的 generation，目标 hex 发生变化仍会拒绝；本规则不承诺所有数值困难都可解决。

## 证据与持久化

raw bytes 和 raw SHA 原样保留。每个阶段另记录规则 identity、阈值 hex、raw/candidate assignment identity、有序 `(name,raw_hex,candidate_hex,delta_hex)`、raw/candidate audit、最大功率平衡残差、是否实际转换及 candidate 判定。candidate 审计失败时也保留已生成的转换 receipt。receipt 在 fresh replay 中从 raw 重新计算，不能由 caller 自报通过。

`normal_h1_hour_replay_v2.py` 只从重审后的 candidate 形成后继锁和最终 carry。numeric pin 同时绑定 native numeric checks 与转换 receipt；projection 使用独立 v2 domain 并绑定规则 identity。完整阶段库存、raw/checkpoint/anchor/fresh 顺序及 no-retry 行为保持。

由于 v1 全链路字节已封存，v2 对 hour replay/archive、incremental archive、stage/full collector、full resource contract、Job 与 gate 逐层使用独立模块及 schema。底层 native capture、原模型、原 numeric predicate、chunk journal、full anchor 和 Windows Job 实现复用未改版本。v1 原成员哈希逐项复核；添加 successor 后旧 gate 的动态 source inventory 不再代表当前全仓清单，因此历史包保全以其冻结 manifest 的逐成员 hash 核验，不将旧 gate 用作 v2 执行入口。

## 冻结验收矩阵

1. 映射区间左端点、阈值外相邻浮点数、最小负 subnormal、`-0.0/0/+tiny`、精确变量范围及其他 continuous 不变。
2. 多项 delta 按变量名排序，raw 不变；candidate 的余额、锁、目标或 chronology 失败仍拒绝。
3. 原 26-stage 保存前缀零 solver 重放；v1 仍拒绝原 raw，v2 仅可形成新的已审候选阶段，缺少其余阶段不能生成完整 projection。
4. tiny 完整已保存 raw 链在 v2 archive/collector/worker 重放、fresh reopen 一致；projection 身份与 v1 分离，raw pins 一致。
5. 转换 receipt 的 delta、赋值 identity、规则 identity 篡改均无法通过 fresh replay；持久化失败窗口仍 fail closed。
6. v2 exact type、资源绑定、Job 身份/quiet/authority、source drift、gate 闭包/review/authority/one-shot 反例全部通过；新 native 入口仍须 consumed gate。
7. 新旧封存工件字节保全、源码差异和相关回归核验；独立 pre-seal findings 闭合后 seal，再由全新 reviewer 作 official review。

## 当前证据边界

本规格不授予 native 运行权。保存 raw 的后继重放是离线诊断，不能改写历史校准，不能证明后续 206 个阶段成功，也不能证明完整小时或全研究资源充分。完整资源准入、共同 Rref/A 发布和完整支持 LB/UB 仍需后续独立证据；所有 formal/ready 标志保持 false。
