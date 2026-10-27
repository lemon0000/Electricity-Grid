# 保留所有fresh读取的pin派生计算复用

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[None1024封装交接](continuation_handoff_20261028_saved_fresh_none1024_rejection_v1.md)，起点a0cba881d6a4c25a3cf126dc6ccbc89aca49d084。上一goal turn为progress：失败、读取证据和53 blobs已远端核验。原累计776.484504500065s、不接受34条；NFC原包14.212736400011636/30s，static6.934642000000167/22、unit7.278094400011469/8、22文件1674286B，全部继续计账。

独立PRE_SEAL设计审查否决“同阶段只读一次或只读两次”的缓存方案：它会删除原中间读取观察点。此后继保留原Path.read_bytes路径、次数与顺序，不缓存文件读取、JSON可变结果、module、compile/code或跨phase数据；真正child source_bookend不改。只在单次metadata check调用内复用exact immutable bytes的SHA派生结果，返回fresh pin dict；变raw、非exact bytes、超cache帽都执行原pin。缓存不保存hash对象或可变dict。相同raw跨路径可共享SHA，不能因此合并路径或减少读取；冲突expected pin仍走原各次断言。

实现以固定v3 driver、其加载的v2 driver和parent27作为三文件allowlist，实际attached module次数由每轮记录，不预设三者都执行。临时替换既有pin/load两个globals；每次load仍执行原loader、创建新module；只包装返回对象，不复用module/code。每个pin自动核相同normalized AST纯公式及sha256/len/dict依赖；before/after核原函数、actor wrapper的code/default/closure cells、未管理globals与held关键primitive/module bindings；finally恢复managed globals并清空缓存。exact bytes cache≤2048项/64MiB payload accounting，超过即回退原计算，不改变结果；该数不是heap/RSS或整链资源准入。新Python包装增加frame，重复SHA内部故障/未知native副作用与完整traceback不作等价声明；Python文件读取异常、变更与expected断言窗口须保持。全部native/FS-ABA/TCB/运行权限仍false。

方法验证包括：fresh dict及外部改dict不污染、每个duplicate位置的持续变化、A→B→A、每个read位置抛同一异常对象、expected冲突两种顺序、路径alias、非bytes/容量回退、原pin首个SHA异常不缓存、globals/primitive bookend、异常退出恢复与释放。仅普通纯Python测试，无native hook或child。原NFC v3的14项不重跑、不修旧终态。

完整方法DAG：register≤1.5s→本次普通unit≤0.5s→独立只读PRE_SEAL findings→两轮old/new与new/old完整冻结check对照≤4.5s→saved≤1.5s→checkpoint≤1s。每个check单次≤2s，不能延时或重试；共old2/new2、0 child/0 cold。读取trace只记path/bytes长度，逐项比原2496行顺序；不额外在每次read内重复SHA，以免掩盖目标计算成本。实际输入pins在阶段前后重核，trace不冒称每行独立raw SHA。单对照不是整F速度结论；仅报告两种顺序的本方法计时、cache计数与读序等价，candidate_adopted=false。

新root最多8文件：driver、registration、unittest_admission、unittest.exit、pre_seal_findings、benchmark.exit、saved.exit、checkpoint。root≤2520018B，组合≤30文件/4MiB；单文件registration/snapshot等沿原帽，unit/admission/exits明确预留。static≤8.5、unit≤0.5、总≤9s；连原包最坏23.212736400011636/30s，static≤15.434642000000167/22、unit≤7.778094400011469/8。不退款或重置余额。任一失败保存raw/partial/费用并拒绝checkpoint，不推进后续验证。

Registration快照本次method/test/scope/driver四源；三个legacy metadata源保持既有冻结文件及expected pin绑定，在构造verification-only reference前fresh读取并核pin，不重复复制历史源码。实际actor loader仍每次完整执行。saved/checkpoint共用严格重放器，重开每个registration pin、exact阶段文件集合、admission/report、四case顺序/trace/metrics/cache释放与派生summary；partial/失败档案不升级为通过。

本范围只完成controller metadata方法证据，不授予新的实际import窗口、完整runtime/P1/role/OwnedChild/Job/F、native校准、科学/资源/正式运行权限。Source49原raw/epoch、所有失败/历史/冻结records和39项并行dirty保持。root唯一writer，既有reviewer只读PRE_SEAL；无official verdict或production seal。编辑/审查/Git与最终记录写入沿原账口径，不计capture；无模拟小时推进。
