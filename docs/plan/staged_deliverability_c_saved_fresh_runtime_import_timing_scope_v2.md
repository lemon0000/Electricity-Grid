# actual import 后继：prefix dictionary 与完整报告校验

2026-10-27，DRAFT_NONAUTHORITATIVE。继承[v1范围](staged_deliverability_c_saved_fresh_runtime_import_timing_scope_v1.md)及[静态size admission](staged_deliverability_c_saved_fresh_runtime_transport_size_scope_v1.md)。RTI v1登记失败原4文件、六helper源码及1.2287622s费用全部冻结；size分析0.3273174/2s，0 child、0 unit。原命令30044 UTF16；同一payload的prefix-zdict/mem8/default候选29560，原payload逐字节回放相同。累计不接受22，前驱static195.50479630001724、pytest366.48897970000326、unittest50.181212600000435、合计612.1749886000209s；原预算超帽与所有失败仍保留。

root唯一writer，独立只读PRE_SEAL，无official verdict/receipt/seal/run authority。core13/probe10仅替换诊断root为RTI v2；BS timing1与namespace timing1复用冻结原bytes。parent10采用已测prefix-zdict压缩，每个实际命令重新核≤30000；loader从sys.orig_argv[6]的既有明文prefix取得dictionary，有限解压上限、eof/unused/unconsumed检查及payload含位置AST/CodeType一致性保持。无新codec依赖，无guard跳过，无Source49或政策变化。

完整路径：登记（先保存transport、exact command units/pin，再判断）→5项逻辑unit→PRE_SEAL→独立startup discovery/profile→唯一actual import诊断→metadata保存。5项覆盖：原BS guard AST不变；arm的held stderr精确身份、成功与arm/import/cancel/trace failure顺序；五个defaults替换反例；mixed/partial stderr与完整report反例；dictionary payload有限回放、含位置AST/CodeType及完整实际argv长度。完整stdout须核canonical newline、schema/case/epoch、18 false gates、status↔exit、kernel PID/creation/image/command、phase、close_calls及清理字段；self-close witness还须两HANDLE各close1、resource CLOSED、DLL cookie关闭、alias移除。没有完整报告时witness=false，不能从timeout推断self-close。Stage parser保留raw及residual，stage_parse_complete恒false。

其余执行与费用边界继承v1：最多2个串行cold child，每个最多2次ENTRY exec，仅第二child最多1次adapter import；watchdog在真正import前arm一次2s/repeat=False，同一finally取消，primary保留，无重试。包括既有扩展依赖import，不构造model/Highs()/solver，不做P1/hold/capture/replay/OwnedChild/Job/F。Native watchdog是本诊断显式观察叶，可能绕过Python audit，零计数不证明无native效果；单样本不证明整个8秒或旧9秒归因。

本后继独立static≤18s、unittest≤4s、总≤22s；登记≤2、unit≤4、PRE_SEAL≤1、startup≤3、profile≤1、import≤8、saved≤2，static余量1s。超帽保留并停，不延期、不重试旧child。root `results/tables/staged_rts24_saved_fresh_rti_v2_non_authoritative` ≤24文件/4MiB，stdout131072、stderr32768、payload131072、profile1MiB、module/cache4096维持；RAM仅观测。冻结前驱账逐项相加，新帽不重置旧帽。编辑/审查/Git、Python初始启动及最终exit序列化不计capture，不是完整wall，无模拟小时推进。

Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875及每个原字节不变。E/U、TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false；本次accepted仅指诊断与保存，不是完整B_S或cold运行验收。39项并行dirty保留。
