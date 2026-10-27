# selected-open固定前缀：guard分段聚合取证

2026-10-27，DRAFT_NONAUTHORITATIVE。起点a555d88bc898fb2545c952102189ff545b295536，接续[RCI交接](continuation_handoff_20261027_saved_fresh_runtime_cache_import_v1.md)。原所有已执行源码/controller/结果/失败冻结；root唯一writer，独立只读PRE_SEAL，无official verdict/receipt/seal/run authority。本scope用于回答guard内部各块的instrumented成本，不等待完整import成功。

新BS census1从cache1复制，_audit完整原body包在外层try/finally中；_audit_entry仅在原语句间加时标，剥instrumentation后原检查顺序/数量相同。cache原全扫描、identity/ownership两遍关系、globals/attrs、image/digest、machinery和metadata setter policy均保持。版本化diagnostic_import_once显式去掉watchdog，arm/cancel均0；activation严格在before_adapter_import成功flush后、import_module前。helper默认强持census依赖函数、native primitives、IO根；IO由namespace graph-plan[3][4:8]注入并在probe校验。固定dict仅聚合诊断，不参与授权或每次重做authority commit，内容不构成独立truth。

只对窗口内同guard、非重入open计时。原_audit inclusive与_audit_entry total包含七个相邻段identity1/runtime_link/cache/globals_attrs/ownership/image_digest/machinery；ownership含第二遍identity。inclusive与子项不能相加；段间bookkeeping/新增binding成本使其不是未instrumented纯CPU。import窗口减guard仅称outside-guard残差，仍含module/native/其他hook/调度/观测开销，不直接称I/O时间。初始/最后snapshot区间含起始帧I/O，不含最后帧输出。

原guard之后安装top-level census_observer，以预创建token的custom audit sentinel核安装恰1；observer纳入helper proof与真实metadata setter保护。固定64个guard已放行的open审计尝试，完成第64次guard后observer先惰化、写prefix_complete、抛独立BaseException子类AuditCensusStop；第64次真实open不发生，不能称64次I/O完成。import提前return则立即惰化/写终帧/受控停止；自然error保留原primary并写终帧；8s仅父端kill兜底。finally惰化，cleanup不凑次数。若stop被吞后仍超时，仅保存prefix/unknown-tail，不声称正常停止。

只输出start及完成数1/8/16/24/32/40/48/56/64的聚合，早停/异常末帧受同一上限：≤12帧、单帧≤2048B、总census≤24576B。只有busy=False后输出，不记录path或event args。clock/encoder/write/flush故障先收集，原guard检查仍执行；原guard/import primary保持，诊断故障作为cause/group。probe exception image共享≤48节点、深度≤6、每组/secondary≤8、type≤80/message≤180，含cause/group；parent核schema及限额。父端只解析完整canonical newline与精确序列帧，重复/乱序/超长拒绝，非JSON及未闭合尾行原样保全。timeout只能报告最后完整prefix；终止时真实inflight/尾段未知，不补算。

执行DAG与硬帽：register≤2s→unit capture≤8s→PRE_SEAL≤1s→startup discovery≤3s→profile admission≤1s→唯一audit-prefix child≤8s→saved≤2s→post checkpoint≤1s；static≤20s（上述static18+余量2）、unit≤8s，总≤28s。1个unit child、2个串行cold child；discovery ENTRY0/adapter0，actual ENTRY≤2/adapter≤1；unit6个legacy fixtures（4原setter+2observer setter）各ENTRY≤2，总unit ENTRY≤12，均逻辑resource/无native self HANDLE。合计ENTRY≤14。0模型/Highs()/solver/P1/hold/capture/replay/OwnedChild/Job/F，不下载/付费。阶段失败/超帽create-only保存并停，不改次数/帧/帽等成功。

14逻辑节点：10个census/AST/default/计数/异常/序列/serializer/完整helper/codec/真实observer setter测试，加4个原module/class code/default setter回归。覆盖拒绝不计passed、64th物理read不发生、activation前0、早return/error、watchdog0、primary/cause以及cache/global/ownership反例。原逻辑fixture不是runtime authority。最长实际argv仍≤30000 UTF16、payload≤131072且逐字节/AST/CodeType一致；parent/probe/core成组迁根。旧8个cache成本节点只复用，不重跑微benchmark。

root `results/tables/staged_rts24_saved_fresh_aoc_v1_non_authoritative` ≤24文件/4MiB，checkpoint脚本在experiments、preseal前绑定其pin；stdout131072、stderr32768、raw import profile1MiB、module/cache4096维持。unit capture本身stdout65536/stderr16384。RAM仅观测，不据unit峰值推actual/F资源准入。

前驱static217.91821880000793、pytest366.48897970000326、unittest54.345750399999815，总638.752948900011s、不接受22条接续，旧120/540/import8MiB超帽不重置。Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875与49字节不变。编辑/审查/Git、Python初始启动和最终exit序列化不计capture，不是完整wall，无模拟小时推进。

E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false；prefix完成不等于CLOSED import、OBSERVED/LIVE或cache adoption。39项并行dirty保留。
