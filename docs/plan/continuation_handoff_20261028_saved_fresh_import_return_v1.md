# F：真实import在1344 open后自然返回

2026-10-28，DRAFT_NONAUTHORITATIVE，起点0fe0ce0ab71f281d5e2a5dadcff27537736ee4e6。承接[真实1024交接](continuation_handoff_20261028_saved_fresh_actual1024_v1.md)，本轮合同为[独立2048及采样停止scope](staged_deliverability_c_saved_fresh_census2048_admission_scope_v1.md)。本轮为progress，宽goal继续active，完整F未完成。root唯一writer；wire_root_review只读PRE_SEAL，没有official verdict、receipt或production seal。

## 已验证的端点

Root为results/tables/staged_rts24_saved_fresh_nfc_v7_non_authoritative，精确**16文件1138658B**；checkpoint.json SHA **b56159068165115b54866169be5fb228cbaad6079081b79b85291443a8d58ce4**，accepted=true、diagnostic_accepted=true。先重开checkpoint、registration、unit/pre_seal、startup/profile、actual receipt及saved；所有本包源码、scope、inputs与记录已执行冻结，不原位改动或重跑。

真实adapter import在**1344个guard-passed open后自然返回**，没有触及2048上限。最终entered=passed=observed=1344，rejected=diagnostic_error_count=0，reason=import_return_before2048，adapter_import_return_observed=true、prefix_complete=false。13个census帧为0、1、128…1280、1344；34个交替graph enter/exit，4个stage精确为loader_ready → before_adapter_import → adapter_import_returned → after_adapter_import_attempt。raw stdout4467B、stderr13061B（census12072B），全部原pin及canonical格式可重开。

自然返回之后仍由既定diagnostic helper抛AuditCensusStop；child exit1、runtime=UNRESOLVED、boundary=FAULTED、resource=CLOSED，close_calls=[1,1]。完整异常链为AuditCensusStop → LocalRuntimeUnresolved → BootstrapImportUnresolved → ValueError(import policy did not complete)。父子HANDLE、DLL directory、pipes/readers/writer/stdin终态完整，无kill、timeout、truncation、reader/cleanup error。

**这不是B_S boundary完成或runtime OBSERVED/LIVE。** machinery observed2、authenticated0、authentication_pending=true，source49_bookend_equal=false、import_boundary_completed=false、runtime_was_live=false、import_profile=null。Source49静态raw pins未漂移与runtime末端bookend不是同一证据；不能互换。无P1/实际role/OwnedChild/Job/F、模型或solver调用，所有native行为认证/科学/资源/正式/run字段仍false。

本次child的source_bookends=2，load_bootstrap_adapter在import之前确已执行runtime.source_bookend；尚未执行的是return之后的post-import/final Source49 bookend及boundary末端绑定，不能称为本次完全没有source bookend。

## 原生采样与解释范围

Actual parent-controller PID40452、child PID40080、原HANDLE648、80B PROCESS_MEMORY_COUNTERS_EX绑定一致。347 attempts/347 samples，native mode且native_sampler_bound=true；child kernel/direct-child/guard PID与parent-controller PID逐项join。无query error、over-limit或sample-limit，终止后没有追加采样。Startup是本包自己的先行证据：parent38984/child40648，12个有效native样本及exit0，随后profile accepted才启动actual。

Observed peak working set：parent **53633024B（51.1484375MiB）**、child **145563648B（138.8203125MiB）**、二者同次peak相加最大 **199196672B（189.96875MiB）**；private commit相加最大 **154185728B（147.04296875MiB）**。每进程256MiB及二进程512MiB只是本诊断的采样停止阈值。PrivateUsage与working set分别解释，采样政策及API定义见本包scope的Microsoft primary references。

memory_observation_source=last_live_memory_guard，receipt/saved/checkpoint投影精确等于已采样child peak；不再调用旧parent的退出后memory查询。该值不是完整生命周期峰值上界，不能与NFC6的终止后peak口径静默合并。continuous_bound_verified、combined_retention_verified、resource_admission均false；这些采样不证明descendants覆盖或128MiB retained-root准入，也不能据高于128MiB的working set直接判定retention违规。

## 时长、调用与保全账

实际import census窗口 **3.827653000000282s**，parent receipt **6.0408364000031725/18.26129170000786s**，外层actual phase **9.363586299994495/20s**。不同口径分开报告；不将返回后尚未执行的finder认证、adapter图或boundary收尾成本补成已测。Cache11→165；entry_total1.4833986000303412s，其中image_digest0.5106628001085483s、cache0.6694503000326222s约占34.43%/45.13%，是重叠的选定open bucket，不是整链成本分解或与旧窗口配对的提速结论。

| 本包阶段 | charge秒 | cap秒 |
|---|---:|---:|
| size | 1.7398736000031931 | 6 |
| register | 1.4743182999955025 | 3 |
| 唯一14-node unit | 8.949498699992546 | 14 |
| PRE_SEAL | 3.1328474000038113 | 4 |
| startup | 3.8526848000037717 | 5 |
| profile | 2.95829870000307 | 4 |
| 唯一actual2048/return | 9.363586299994495 | 20 |
| saved | 2.9697845000046073 | 4 |
| checkpoint | 1.8995508999942103 | 3 |

本包static **27.39094450000266/49s**、unit **8.949498699992546/14s**、总 **36.34044319999521/63s**，剩余26.659556800004793s留原包。最新累计static **386.22631980005394**、pytest **366.48897970000326**、unittest **113.75259559999176**，总 **866.467895100049s**，不接受仍 **37条**。旧失败/余量完整保留，无退款、重置或跨包转移；capture计费不是全部编辑/review/Git/Python启动wall。模拟小时推进0。

旧57文件4020082B，加本包共73文件5158740B；这些是所列结果roots的保全计数，不是工作区占用或合并storage准入。新registration实际672529B、size上界673553B≤786432B；命令29706/30000 UTF16。输出上界21680B census+8960B graph+264B stage=30904B≤32768B，saved固定body上界2444B≤4096B；正常18帧与本次自然返回13帧分别解释。

## 实现和独立核验

core34/probe32/parent31、census2048_v1、native fixture6、none_census2048_v1 tests由固定constructor精确构造；原1024各包不动。诊断helper schema v5、20帧帽及新schedule与parent一致，科学阈值未改；memory_drain_v1和独立fixture已集成。生产drain不接受sampler注入，test模式不能通过native healthy验证；函数/actor/code/defaults/closure/kw-map和关键primitives前后核，入口漂移反例确保0副作用，pending reader及pipe-close注入由fixture finally收尾并验证拒绝。

本包登记14 helpers、347 direct inputs、1086 effective inputs，继承1072及新增输入精确合并。完整unit为30帧、14/0/0/0、runner2.993s、PID38792/exit0与收尾完整，实际调用新增2048、采样、PID/source/projection及清理fault cases；不是仅有测试文件。独立PRE_SEAL逐项核347 inputs、14 helpers、49 Source、嵌入源码与原streams，并核startup native、actual自然返回、saved重放与全root。它不产生official状态或任何运行权限。

Source49原raw/epoch仍acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875。当前没有活动实验进程。39项并行文稿/插图/文献dirty原bytes保持；四导航仅发布新前置段+HEAD正文，不能报告全局clean。最终hash以包含本交接的commit与remote实时回读为准。

## 下一步

不再放大import窗口。当前diagnostic_import_once在真正返回后抛stop，阻止了load_bootstrap_adapter后续的authenticate_machinery、13函数/2类roots、namespace图、post-import/final Source49 bookend、retention、boundary.close与runtime.finish_import。下一步按[返回后续接准入草稿](staged_deliverability_c_saved_fresh_post_return_admission_scope_v1.md)先审实际DAG/调用倍数、getter重入、图/retention及完整保存成本，再建立独立后继；不能直接恢复本包的已关闭child或把本次return当OBSERVED。
