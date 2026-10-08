# RQ2 连续输入可用性与 provenance 审计 v1

状态：DRAFT_NONAUTHORITATIVE  
日期：2026-09-12

本审计回答一个限定问题：冻结的 power v4 与 workload v3 marginal packages 中，哪些 24 小时块具有同
split、同内部轨迹的唯一下一块，哪些小时在该冻结 margin 中不可用，以及现有字段距离完整 continuous
joint-service 合同还缺什么。它不注册 power/workload coupling、deadline、accounting period 或恢复参数，
不执行 dispatched grid、planner 或 solver，也不打开任何 formal/result/claim/security gate。

## 1. 绑定与方法

审计逐成员验证两份 package manifest，并直接绑定各自 builder config、builder 实现；power 另绑定 N-1
chronology 模块。上一轮 boundary config/audit/boundary/runner 及其三个结果文件也逐字节验证，未被本轮修改。

- power manifest：28bc2c3c1ee3ba0ef6c940aec56f66d49587b5f2895d0e6b0b83fb0b6360cc63
- workload manifest：62f2ec5eefd0c651d8b970a16fce4fb6336ccb75ab09e3d2c67386cc26edb524
- 本轮 config/implementation/runner：
  0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5 /
  c7f2c4678cf20a7e61c159e661774e13607f526bff6d487a97cbcd1b100f5a78 /
  dcdacf5d94426746541e53813f48ad9af4a66c6e82155833f2c060a6c5093c7e

每个 block 必须恰有 offsets 0–23、连续 source hours、单一 split/概率；power 还必须有单一 outage seed、
UTC timestamp 每小时递增，且逐时 active event 的 ID/type/UID 与冻结 event schedule 一致。下一块只在
相同 split 与相同 trajectory identity 内按 next.source_start = previous.source_end + 1 建立。重复起点、
重叠、gap、seed 或 split 变化都不能成为同一链的 successor。

workload trace identity 不是 CSV 中的现成 trace_id，而是由 source SHA、builder/config、package summary、
training peak 与 divide_by_training_segment_peak_occupancy 方法共同绑定。逐行用 Decimal 验证
requested_gpu_occupancy / training_peak = workload_fraction，不修改或截断 raw fraction。

## 2. Power margin

冻结包中有 1,071 个 blocks、25,704 行，按 split × outage seed 形成六条连续片段：

| split | seed | blocks / hours | frozen-margin source range | block links | 在该 split 的冻结 margin 中不可用 |
|---|---:|---:|---:|---:|---:|
| training | 20260822 | 181 / 4,344 | 0–4,343 | 180 | 4,344–4,391（48h） |
| training | 20260823 | 180 / 4,320 | 0–4,319 | 179 | 4,320–4,391（72h） |
| training | 20260824 | 180 / 4,320 | 0–4,319 | 179 | 4,320–4,391（72h） |
| holdout | 20260822 | 181 / 4,344 | 4,440–8,783 | 180 | 4,392–4,439（48h） |
| holdout | 20260823 | 176 / 4,224 | 4,560–8,783 | 175 | 4,392–4,559（168h） |
| holdout | 20260824 | 173 / 4,152 | 4,632–8,783 | 172 | 4,392–4,631（240h） |

同 seed/split 内共有 25,698 个连续逐时 source+timestamp links，active-event ID 合法变化 864 次；在 block
边界上保持同一非空 outage event 的 links 为 training 439、holdout 419。这说明 event ID 随时间变化是
同一 seed trajectory 内的正常状态变化，不能把 event ID 固定不变误作 continuity 条件。

三个跨 split outage events 及构建器的保守整块排除为：

| seed / event | 实际 event 区间 | event hours | 被排除的整块覆盖区间 | package-level hours |
|---|---:|---:|---:|---:|
| 20260822 / event_0094 | [4,362, 4,419) | 57 | 4,344–4,439 | 96 |
| 20260823 / event_0023 | [4,331, 4,547) | 216 | 4,320–4,559 | 240 |
| 20260824 / event_0087 | [4,336, 4,625) | 289 | 4,320–4,631 | 312 |

这些区间是 frozen margin 因 exclude_every_block_touched_by_cross_split_event 而没有可用 block，并不声称
上游 RTS/CFE source 没有这些小时。若未来要恢复这些小时，必须新建有 provenance 的 derived package 和
split/event 合同，不能直接把上游行塞入当前冻结 margin。outage chronology 是
sampled_from_published_rate，不是观测事故或经验事故概率。跨 seeds 相同 source hour 的 timestamp/load/CFE
相等只证明共同外生基线；不同 seed 的事故轨迹仍不同，不能相互拼接。

## 3. Workload margin

workload 每个 split 有 34 个 blocks / 816 小时：training 为 0–815，33 个 block links；holdout 为
821–1,636，33 个 block links。training 的 816–820 与 holdout 的 1,637–1,641 各有 5 小时因
incomplete_terminal_block: drop 未进入冻结 margin。两条片段共有 1,630 个连续 source-relative-hour
links；CSV 没有绝对 timestamp，因此不能与 power source_hour 宣称同钟。

1,632 行全部通过 training-peak normalization 恒等式。raw training maximum 为 1；raw holdout maximum
为 1.070370705271957780430251624。holdout 有 6 个小时、3 个 blocks 超过 1，source-relative hours 为
1198, 1206, 1207, 1208, 1209, 1267。审计保留这些 raw 值；旧 v5 的
occupancy = min(raw workload fraction, 1) 是另一个模型映射。continuous successor 必须显式决定适配语义，
不能让原型的 [0,1] 输入检查静默 clip 或把 raw 包误报为不可复现。

## 4. 双 margin 邻接与合同缺口

只有 power 与 workload 两侧都存在 successor 时，当前 marginal pair 才有结构上的双边下一块候选。因此：

- training：538 × 33 = 17,754
- holdout：527 × 33 = 17,391

这只是 Cartesian marginal 的 potential adjacency，不是已注册 joint coupling、概率或物理同钟关系；一侧
有 successor 不足以构成 joint continuation，跨 split links 为 0。

冻结字段能证明 CFE call fraction 与 dimensionless requested-GPU occupancy 存在，但不能证明以下合同：

- dispatched grid_need、共同物理时钟或 workload absolute power；
- 观测 flexible fraction、call limit、track-compatible recovery headroom、maximum recovery power 或
  recovery efficiency；
- 业务 flexibility 的 duration/event-count/energy/debt limits；
- accounting-period ID、service deadline、checkpoint 或 recoverability。

这些字段当前是“尚未绑定未来 continuous preregistration”，不表示未来不能在用户明确授权下采用机制假设；
但本审计不选择数值，也不允许零 tail、无依据 reset 或结果后调参。故
raw_chronology_candidate_available=true 只指各 frozen margin 内存在相邻片段，
full_joint_service_continuation_ready=false 与 continuous_scientific_protocol_registered=false 保持关闭。

## 5. 工件与复现

运行命令：

    & 'D:\Miniconda3\envs\rq2-executor-v2-audit\python.exe' -B -m experiments.audit_rq2_joint_deliverability_continuation_v1

输出位于
results/tables/rq2_joint_deliverability_continuation_availability_v1_non_authoritative/，拒绝覆盖已有目录。
summary.json / chains.json SHA-256 分别为
faba770bf8f3d83229f840fc1074939742e847bd55ab793b63264cb2322dd45e /
0f661707d4ebb6ceb6f12073e6426a03b542322324df8a4f99b6d229ced8fc48。
当前证据只完成执行计划中的 continuation availability/provenance audit；完整 scientific successor 仍须
预注册 coupling、accounting/deadline、raw>1 映射与 censoring estimand，并接受 fresh independent R4 review。
