# B_S固定256前缀完成，cache校验成为优化候选

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[完整导入失败交接](continuation_handoff_20261028_saved_fresh_full_import_timeout_v1.md)，起点`d59889136b28103d84f6fc46ecc0148bce211191`，执行按[固定范围与预算](staged_deliverability_c_saved_fresh_prefix256_scope_v1.md)。root唯一writer，既有reviewer只读PRE_SEAL，没有official verdict、production seal或运行授权。宽goal继续active，完整F未完成。

## 本轮已完成的真实路径

AOC9的size/register、6/6 unit、PRE_SEAL、startup/profile、唯一prefix256、saved和checkpoint均accepted。command **29972/30000 UTF16**；原decoded payload字节变换、位置AST与CodeType等价通过。core24/probe21只迁移同长度root，child v1 envelope保留；helper相对image-pin原件只改五个census函数body的limit/schema/schedule/消息，其余AST及全部FunctionDef header不变。科学adapter、Source49、guard、image pin和缓存策略均保持。

父端case charge **3.150436500000069/cap7.080164799997874s**；外层audit_prefix charge **4.547520400003123/8s**。真实10帧passed序列为 **0,1,32,64,96,128,160,192,224,256**。每帧九个bucket count等于passed，起始时钟固定、cache增量公式一致，machinery单调并与child最终报告相等，诊断错误0、拒绝0、最后无inflight/last_incomplete。第256次guard-passed观察后按设计抛出`AuditCensusStop: diagnostic_prefix_complete_256`，窗口内第256次physical open前停止；该边界另由合成方法测试证明，不能把256解释为全程序文件打开总数。

child exit1/status failed是预设诊断终态。runtime **UNRESOLVED**、boundary **FAULTED**、resource **CLOSED**，self HANDLE各close1、DLL关闭、namespace alias移除；父端HANDLE、stdin、pipes和writer/readers全终态。`drain_reason=null`、killed=false，cleanup/reader/writer errors空，stdout4442B/stderr10099B均完整未截断。primary和完整secondary链与原64前缀只在固定stop消息上作机械替换：`LocalRuntimeUnresolved → BootstrapImportUnresolved → ValueError(policy_terminal)`的未完成链保留，不将它们误称清理成功或隐藏。

adapter import返回未观察到，retained_modules=0、source_bookends=2。machinery observed/authenticated都为0、pending=false；optional/blocked Popen各1、internal introspection6，这些计数不等于M/D认证、NumPy SVE最终确认或完整import完成。Source guard的source_open_attempts=686属于其自身计数，不与census窗口256混同。全部nested authority与科学/资源/正式门禁维持false。

direct child peak working set **66039808B = 62.98046875MiB**，error=None；仅支持本次主动终止前缀的观测，不证明完整import或F的RAM上限。

## 新的性能证据

census begin→最终snapshot为 **1.0025682999985293s**。以下值来自同一次真实256窗口，不能把重叠的inclusive计时相加：

| 计时桶 | 累计秒 | 解释 |
|---|---:|---|
| audit_body_inclusive | 0.40380050009844126 | 窗口wall的40.28% |
| entry_total | 0.3984172000273247 | 包含下列entry分段 |
| cache | 0.20416659995680675 | entry的51.24%，audit的50.56%，窗口的20.36% |
| image_digest | 0.1374206999244052 | entry的34.49% |
| ownership | 0.023833799961721525 | 保持原检查 |
| identity1 | 0.02258650005387608 | 保持原检查 |

cache从 **11→48项（新增37）**。同为32事件的32→64段cache耗时0.010268199992424343s，224→256段为0.052787000029638875s；最后32事件cache占该段audit的 **69.56%**。这支持优先检查cache随条目增多的成本，不能单凭该样本归因完整导入超时，也不能外推完整import、native或F的时长。

源码读回确认`_check_cache`每次重开并检查全部predecessor identity和新增cache项，对每个新增key构造Path并调用两个根的`is_relative_to`。当前已pin runtime leaf为`D:/Miniconda3/envs/compute/Lib/pathlib.py`；其690–700行通过`with_segments`构造other并检查自身/parents。下一候选是检验同一调用内的规范化parts前缀比较是否严格等价并降低反复祖先构造成本，**尚未实现或采纳**。

下一实现须独立successor：先写等价边界与成本预算，保留每个event的predecessor identity、key/type/path、finder kind和finder.path检查，覆盖大小写、分隔符、盘符/UNC、`.`/`..`与错误顺序；不增加文件系统解析或跨event结果缓存。需独立oracle、方法收益与真实连接证据后，才能再次考虑固定预算的完整import诊断。不能在旧AOC9或full失败root上改字节或重跑CLI。

## 预算与恢复入口

root：`results/tables/staged_rts24_saved_fresh_aoc_v9_non_authoritative`，**25文件/955638B**，上限30/4MiB。1个unit child、2个串行cold child已全部终态。本轮没有新未接受记录，先前28条全部原样保留。

| 阶段 | charge秒 |
|---|---:|
| size | 1.09940440000355 |
| register | 1.101988499998697 |
| 6项unit | 2.845525799995812 |
| PRE_SEAL | 1.3624113000041689 |
| startup | 1.8968252000049688 |
| profile | 1.1859709000054863 |
| prefix256 | 4.547520400003123 |
| saved | 1.1836237000024994 |
| checkpoint | 0.7468669000008958 |

scope static **13.124611300023389/22s**、unit **2.845525799995812/5s**、总 **15.9701371000192/27s**。累计static **281.14382750002846**、pytest **366.48897970000326**、unittest **74.28716270000223**，总 **721.919969900034s**，不接受 **28条**。失败费用不退款，scope余量不重置历史账；编辑/审查/Git、Python初始启动和最终记录写入沿原口径不计capture，不是总wall，没有模拟小时推进。

恢复先读本root `checkpoint.json`、registration、size、unit报告、PRE_SEAL findings、各phase exit、saved_report和probe_import_discovery.receipt。saved和checkpoint重放同一strict实际raw/record矩阵；checkpoint的diagnostic accepted只针对固定256前缀。新父端保留原drain_reason，partial/early-return/no-report/nonempty-drain均拒绝；startup profile writer/size/register/profile统一131072B，未扩资源帽。

Source49 epoch仍为 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**，49份raw和所有旧失败/root保持。下一步仍是cache候选等价证明与完整B_S import闭合，之后还有OBSERVED profile、LIVE故障矩阵、真实producer/owner/Job/bootstrap、ACK/issuer/permit、quiet/返回和父端采用。E/U、独立TCB/native、完整runtime/P1/role/permit/F/science/resource/formal/run authority均false。

39项并行文稿/图件/文献dirty保持；发布只覆盖本轮scope与四导航前置段，导航原工作区正文保留。远端提交号以发布后实时读回为准。
