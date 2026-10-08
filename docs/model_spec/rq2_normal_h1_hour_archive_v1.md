# H1 单小时阶段存档与流式数值重放候选

状态 DRAFT_NONAUTHORITATIVE。独立 hour replay/archive 类型、schema、key 和限额；旧 short native、20-stage replay、32MiB archive、source episode及冻结产物不改。

## 定位与身份

H1HourReplayLimits 的 max_stages≤232，max_variables/max_constraints 各≤1000000，exact int 拒 bool。这是处理已存在报告的大小域，不是 native calls/time/commit/wall 预算或运行授权；每份 raw 仍≤16MiB。request key绑定当前 normal input、relative hour、solver specification、replay limits和实现。absolute source timestamp/selection标签不进入计算key。

DevelopmentH1HourArchive 深拷贝声明，以当前 H1 模型机械导出 operating cost→排序 committable commitment→排序 all-generator generation。chunk binding另含 source audit identity、外部 parent intent head、source lineage pin、完整stage order和实现。外部parent/source pin只是待集成引用，parent_intent_verified/source_authenticated仍false；本层不证明parent intent实际存在。

存档使用已审1MiB chunk primitive和单小时独立数据库；每个stage最多16块，stage metadata≤256KiB，预算覆盖 n个报告加terminal。分块head表示字节存储进度，不能用作normal completed_hours。

## 报告验收与持久化顺序

record_report 接收已有原始 bytes，本身没有 solver runner。对当前stage重建模型和stage identity，检查raw的schema/solver选项/规模/structure/运行通道一致性，再用原 verify_numerical、normal专属numeric predicate和strict H1 assignment audit逐一验收。连续canonical lock原样保留；commitment只用原先已批准的整数化规则。下一阶段locks只能来自此前验收通过且持久化成功的stage。

顺序为：重建旧prefix→审计当前raw→原子append metadata与原始bytes→fresh物理readback→fresh语义重放→更新owner的canonical locks。metadata绑定index/objective/stage identity、prior-lock digest、raw SHA、canonical lock与numeric predicate摘要。只有typed H1ReportAuditRejected（raw decode/binding/numeric/assignment验收失败）才将原raw保存为stage_rejected，锁不推进且无projection；该状态不表示数学不可行。

request/current/model构造、replay规模限额或实现/声明失败直接抛出并锁止，不写成stage_rejected。commit/no-op/已commit后异常/fresh readback失败为持久化unknown：锁止owner，不返回新head，不自动重试，已有原始前缀保留。若收到的bytes超限或落盘失败，不能宣称该raw已完整保存。仅awaiting_terminal状态可finish，terminal projection和lock列表由完整raw重算并绑定；terminal之后拒绝任何报告。

## 单小时重放

inspect/reopen持有同一chunk owner guard和SQLite read snapshot，先一次_chunk._scan完整验证字节prefix，再一次按event顺序读取。每次仅组装单份≤16MiB raw，审计后释放，不构造整个小时reports tuple。模型、canonical locks、数值通道与final projection全部重算；metadata/terminal自报值不作为证明。缺失、重排、重复、额外report和terminal篡改均拒绝。

完整数值投影使用独立 H1HourReplayedProjection 类型，和旧类型互不兼容。numerical_chain_recomputed只表示数值重算，solver_calls_by_replay=0；native_execution_authenticated、exact_mathematical_certificate、published、formal_result均false，不返回可执行boundary。

## 开发证据与资源边界

测试直接读取此前已留存的三阶段sample_archive.json（SHA256 0a8f3ddbd3dd6895dc957378e361a88d3ef27ef08c419db744c1a7d0cd335fca），全部solver入口禁用；新旧projection payload逐字、projection identity与locks一致。未重复运行小例solver，也未进行真实RTS 232-stage native链。

当前record_report为每阶段重验完整prefix，包含数值重放，写成本仍按stage数二次增长；finish也有独立前缀重放。只读inspect对整个小时进行一次物理scan加一次有序读，数值重放stage数线性。不能把小例耗时外推为真实网络资源预算。

下一层仍需collector-owned逐阶段sink、durable parent intent和unknown恢复、实际source/normal前驱重验、受控增量写及完整物理预算；当前API接受提供的报告，不能证明历史调用时序或宣称已实现native运行期间的stage-sink安全。collecting存档可继续接收已有证据，但不授权重试任何native调用。


standalone replay_stream 在已审 solver_calls_forbidden guard 内消费报告iterator；已知solver入口被拒绝，即使iterator吞掉异常，context退出仍拒绝结果。guard实现哈希进入新key。测试另以固定真实RTS来源验证232阶段声明可构成replay key，但空stream仍incomplete，旧20阶段入口仍拒绝；没有真实232-stage数值链或native资源证据。
