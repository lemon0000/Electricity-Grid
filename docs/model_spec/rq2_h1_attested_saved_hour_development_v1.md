# H1 saved-only 持久复核链（开发）

状态为 DRAFT_NONAUTHORITATIVE。新增 `h1_attested_saved_hour_development_v1.py`
继承上轮 saved-hour 生命周期，保留旧源代码、测试、封存与开发证据字节。
根代理唯一写入；必须完成独立 R3 只读开发审查，不能代替 official verdict。

## 持久顺序与失败窗口

小时 binding 固定科学 request（包含 packet、specification、limits 和 replay 实现）、
stage count、开发依赖 pins、旧 adapter binding、raw binding 和 timing binding。
另绑定 packet.audit_identity，覆盖 source timestamp/time basis/workload audit；
保持原因果计算 request key 的语义不变，同时拒绝计算 inputs 相同但来源时钟不同的 packet。
每 stage 的固定顺序为：

1. 构建带完整 prior locks 的实际模型；timing begin 持久确认。
2. raw intent、完整原 raw、fsync/fresh readback、raw receipt。
3. 固定版本 saved guard 执行成功，写入 guard receipt，绑定 raw receipt、request、
   stage identity、guard 返回值、小时 binding 和上一 stage commit。
4. 真实 v3 `_audit_stage` 成功，重验科学与开发身份，完整保存 generation mapping
   （cap 256 KiB，包含 changes 的原值/新值/差值及 raw/candidate audit），写 science summary，绑定 guard
   receipt、replay identity、stage identity、lock hex、raw/numeric SHA、assignment
   SHA 及 generation mapping SHA。完整原 witness 始终保存在 raw 中，转换不修改它。
5. raw outcome 与 capture timing end fresh 确认。
6. stage commit 绑定 science summary、raw outcome 和 capture timing end；commit
   fresh 确认且 post-check 成功后才推进内存 lock。

guard receipt 写入失败不进入科学 audit；science summary 失败不产生 raw outcome；
commit 不确定不推进 lock。任一异常 poison，保持部分文件，不覆盖、不重试、不恢复。
若科学拒绝附带 generation mapping receipt，先按相同 cap 保留完整 receipt 再传播
拒绝；不产生 science summary 或 raw outcome。超 cap 时同样保留原 raw 并 unresolved。
已落盘但确认失败的 commit/terminal 不能自行升级为成功返回证据。

完整 finish 先从所有 durable raw 执行旧 v3 `replay_stream` 并比较 locks，再完成 raw
与 timing terminal。随后保存 projection payload（cap 256 KiB）及小时 terminal，
后者绑定 binding、最后 stage commit、projection identity/bytes SHA、report/stage/
numeric 向量 SHA、raw terminal、timing terminal 和 stage count。最终独立 reader
成功后才向调用方返回 projection 与外部可保留 terminal pin。

## 独立重开

reader 必须收到调用方独立保留的 binding 与小时 terminal pins；不能用失败根目录
自行计算的 pin 替代此条件。reader 限量列举 exact 目录/文件集合，检查完整 raw 与
timing chains，确认实际 build/capture/audit/fresh_reopen/terminal 计时事件序列。
逐 stage 重新构建实际模型，执行 saved guard 与 `_audit_stage`，精确比较所有 receipt
和 commit；再完整调用 `replay_stream` 比较 locks、三个身份向量及 projection。
完整 mapping 文件必须与科学复核返回值逐字节规范编码一致，不能以摘要替代差值保存。
返回前对读取的所有文件重新检查完整 bytes/hash/identity，并复核目录集合和输入/实现。
整个科学过程禁止已知 solver 入口。未知 terminal pin、缺失、extra、部分写、tamper、
可见漂移或 fresh view 变化均 unresolved。

`saved_hour_evidence_complete` 与 `saved_guard_receipts_recomputed` 仅说明本次独立
saved-data 复核链闭合；它们不认证历史 native 执行或 live reverse map。计时自身
开销未独立分离，最终 projection/attestation/reader 开销在旧 timing recorded window
之外；不能证明 2440 秒分项预算。文件 fsync 不构成断电后目录项持久保证，身份检查
不声称防御恶意 ABA。
guard/science receipt I/O 计入 audit span，raw outcome 计入 capture；stage commit
及阶段后的 post-check 位于 terminal tick 之前，归入 window 内未分类时间。小时
projection、attestation terminal 和最终独立 reader 则在该 tick 之后，未纳入 window。

## 短验证及资源口径

真实 RTS origin 的前两个 stage 使用原 raw，保存和科学复核后保留逐 stage commit。
完整成功/失败链使用明确的 test-only tiny 三 stage synthetic fixture：复制旧样本，
仅将 TimeLimit 元数据 1→5 与 synthetic spec 对应，保留源 bytes/SHA，新 SHA 不同。
所有 guard/audit/replay 代码真实执行；该 fixture 不构成 native/scientific witness，
不证明新的 5 秒 native 采集或完整 RTS producer/carry 覆盖。
另以既有 v3 stage 25 已审 mapping 验证原样持久化：1838 bytes，唯一 changes 包含
`201_CT_2` 的原负值、零值和精确差值；源 raw 与 mapping SHA 固定。该测试仅验证新
存档器保存完整 receipt，不重做科学规则或 0..25 prefix，也不构成新增小时证据。

每 stage 新增三个 2048-byte metadata 上限和一个 256-KiB mapping cap，另加 binding、
terminal 和 256-KiB projection cap。232-stage 单入口内部规定路径上界为
3959119872 logical bytes、3261 files、236 directories。此界包括原 ingress/timing 副本，不包含外层 parent、
旧 SQLite、Job 日志、任意 callback 写入或文件系统 allocation/目录开销。

后续仍需生产 collector/独立 hour Job、完整逐小时来源/carry、全分段计量与 observer、
typed missing-tail/失败分类、整任务资源预算、实际 reuse DAG/task manifest、共同
Rref/A、完整支持 LB/UB、准入、封存和全新 official review。producer/native export/
collector/resource/formal-ready/formal-result gates 均保持 false；新 native 仍须
针对具体就绪包单独明确授权。
