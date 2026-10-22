# M232 origin packet 的有界成本与保留数据诊断

R3 / DRAFT_NONAUTHORITATIVE，root唯一writer，既有reviewer仅只读PRE_SEAL。本包从已验证2910绑定和已有M232资料继续，不改变source/helper/owner/config或任何历史结果。

问题是source v3在真实232-stage网络的一份H1CurrentNormal及其三字段pin的原retained_size成本/足迹，不是192小时真实carry验证。ChildInspection实际只存scalar字段和final Projection bytes，没有保留232份raw stage reports；本包不伪造ChildInspection、不创造after boundary、不拿旧异构projection当当前source结果。

固定路径：fresh old2910+新code/request/config绑定 → 一个fresh子进程 → 原solver deny context → 原load_pinned_current（旧shape request的training power/workload row0、seed20260822）→ exact H1PinnedObservation/declaration/source/network/config核对 → 原assemble_current_normal(relative_hour=0) → actual stage_order与旧expected_stage_count均为232 → 原v3_remember_packet一次 → 原_validate_all_packets一次 → 9个字段、1次whole-pair及1次all_packets容器的原retained_size → 原validate_pinned_current再load一次 → 所有已审计data/config打开文件前后SHA → 五个solver deny slots逐对象核恢复、terminal、进程清理和全部绑定复核。不构建Pyomo模型，不调用Reader/source.prepare_many/selector/normal Job/native solver，不下载外部数据。

复用旧shape加载+装配约1.529s、source revalidation1.406s的路径证据，另加imports、v3 digest/retained walk、文件hash及监控开销。总60s、无activity30s，RSS采样768MiB，logical输出64MiB，2s采样/30s心跳；仅允许直接System32/conhost helper，超限即按PID/create-time清理，失败完整保存，不自动重试或延时。阈值是采样watchdog，不是绝对wall/RSS上界。

审计Python文件写入：仅允许owned output，data/config最多512个distinct opened文件在首次open前及结束后SHA；不能声称覆盖未审计native I/O或hostile ABA。source loader本身保留原manifest/package/row核验。输入原件不改，全部新输出保存在本目录。

输出包括一份真实h0 packet+pin的v3_packet_accounting_bytes、all_packets容器另计的recursive bytes、分阶段耗时、9字段各自去重的足迹（不可相加为unique总值），以及168/170/192乘以同一h0会计单位的条件乘积。retained_size是递归sys.getsizeof，_remember_packet返回量不含all_packets字典/key开销；跨小时每次walk有独立seen，重复计共享对象。这些量不是serialized bytes、RSS或物理内存。

乘积不是H192的上界、下界或预测，未证明其他小时≤row0；未覆盖其他row/future carry、selected frame/proof/evidence容器或allocator/RSS。即使乘积小于128MiB，也不打开全时域retention或任何formal/resource/adoption门。后续必须依据实际结果和完整拓扑/来源条件补适用性及净成本。未执行的pre-review plan_v1及当时worker/runner/design原字节保留在before_preseal_01；实际登记为plan_v2。
