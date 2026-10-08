# H1 持久计时与 saved raw 科学复核入口（开发）

状态：DRAFT_NONAUTHORITATIVE。根代理唯一写入，R3 独立只读开发审查。
本文件对应新增 experiments 模块；旧 v2/v3、旧开发证据绑定文件均保持原字节。

`h1_durable_timing_development_v1.Journal` 使用 create-once 独占文件，每个 begin/end
固定前一记录 SHA256、sequence、单一进程/线程/clock domain。begin 完成 fsync 和稳定
fresh readback 后才进入 body；end 按 LIFO 闭合。允许同一 stage/phase 多次出现。
最多 4096 spans、8193 events，每文件最多 2048 bytes。reader 独立以相邻 event
区间归属最内层 span，重算 exclusive totals，未归属时间单列。完整 totals 必须有
独立保留的 terminal pin，且文件集合、hash chain、完整 fresh view 一致。
成功 receipt 返回 request、binding 和 terminal pins；后继外层需独立绑定它们。
该前提不能由失败 journal 根自行证明，调用方不得自行 hash 失败后遗留 terminal 来
替代成功返回并独立保留的 pin。
缺尾、部分写、异常、clock reversal、未知 terminal pin 均返回 unknown，aggregate 为
None；失败 owner poison，不重试、不恢复、不覆盖。文件 fsync 仅支持进程中断证据，
不声称 Windows 目录项在断电后持久。

计时口径：begin 写盘处于新 span 内，end 写盘处于父 span 或未分类时间内；binding
写盘在未分类时间内。terminal tick 之后的最终写盘、fresh inspection 和返回 receipt
不在 recorded window 中。observer 开销尚未独立分离，因此 instrumentation coverage、
component_budget_verified 均为 false，不能证明 2440 秒 non-solver 预算。

`h1_guarded_ingress_development_v1.SavedStages` 的顺序是：
timing begin → ingress intent → 完整 raw/fsync/fresh readback → raw receipt →
固定版本 saved_report guard → scientific consumer → ingress outcome → timing end。
固定 guard、grammar、serializer、ingress、timing 和 adapter 的实现 pins 写入 binding，
每次消费前后核对。callback 成功本身不是科学接受；中断后也不从 callback outcome
推断 guard 已独立认证。raw 超过 16 MiB 或 producer 没有完整返回时，不能保证完整保留。
`guard_execution_durably_attested=false`：raw outcome 未链到 adapter binding 或独立
guard receipt，因此不能从磁盘工件证明某 guard 曾执行；尚需后继持久接线。
raw 在 16 MiB 内但超过条件 grammar bound 时，先完整保留再拒绝。

`SavedHour` 由真实 packet/specification/limits 派生 request key，逐 stage 构建带完整
lock prefix 的模型，在 raw 保存后执行 guard 及旧 v3 `_audit_stage`，仅在 outcome
成功后推进 lock。入口在 `solver_calls_forbidden` 内。
stage audit 前及 raw outcome 返回后、lock 推进前，均重验 request key 与科学实现身份；
后验漂移可留下 raw outcome，但不得推进 lock，整个 SavedHour poison。此检查针对
边界可见漂移，不声称防御恶意瞬时修改并恢复的 ABA。
完整小时 finish 必须重新读取全部保存 raw，调用 v3 `replay_stream`，比较 locks，
再完成 terminal。
部分小时没有 projection，拒绝 finish 并 poison。当前短验证覆盖真实 RTS origin
前两个 stage 的完整科学复核；未验证该入口的完整 232-stage finish，不能提升整小时
或未来 carry 的覆盖状态。此入口尚未接入独立 Windows hour Job 或生产 collector。
完整 finish 的短验证另使用 test-only synthetic fixture：从原 tiny 3-stage archive
复制 bytes，仅将 TimeLimit 元数据 1→5 与 synthetic spec 对应，源 SHA 和源文件保留，
新 raw SHA 不同。实际 guard、`_audit_stage`、`replay_stream` 均执行，测试成功闭合及
fresh replay/raw terminal/timing terminal 失败停止。这不证明 5 秒 native 采集，
不构成 native/scientific witness 或 producer coverage，与真实 RTS 两 stage 证据分列。

storage_bound 是单个 adapter 的逻辑文件上界：raw 保留旧 16 MiB cap；每 stage
至多四个 raw 子文件；raw 根最多三个 metadata；计时按每 stage 三个 spans 加两个
全局 spans；另计 adapter binding。它不含外层 parent、旧 SQLite 副本、Job 日志、
文件系统 allocation、目录开销或其他全任务产物，不能替代资源准入。
上界限于 SavedStages/SavedHour 内部规定路径，不涵盖任意 callback 额外写盘或额外
调用公开 timing.span。232-stage 情形为 3896610816 logical bytes、2330 files、235
directories；仍无 filesystem allocation 上界或整任务 admission。

仍需：完整 worker/独立 hour Job、live native map guard、source/build/native/capture/
audit/SQLite/anchor/terminal/telemetry 全分段接线及 observer 计量、失败分类与 typed
missing-tail、完整新增副本资源预算、真实 reuse DAG/task manifest、共同 Rref/A、
全支持 LB/UB、完整资源准入、封存与全新 official review。任何新 native 执行仍须
用户对具体包另行明确授权。producer_coverage_proven、native_export_coverage、
collector_integrated、resource_admission、formal_execution_ready、formal_result 均为 false。
