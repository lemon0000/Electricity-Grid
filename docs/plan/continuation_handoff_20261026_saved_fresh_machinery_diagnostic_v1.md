# C/F：Pyomo finder注册差异已取证，待精确迁移策略

2026-10-26，DRAFT_NONAUTHORITATIVE。接续[前序失败交接](continuation_handoff_20261026_saved_fresh_import_policy_cold_v1.md)与[单次取证范围](staged_deliverability_c_saved_fresh_machinery_diagnostic_scope_v1.md)。root唯一writer，独立只读PRE_SEAL，无official verdict/receipt/seal。宽goal继续active。本轮生产ENTRY、tests和policy均未修改；Source49仍为42项普通回归对应epoch `a5bd60823fc501feddd91512a9c16ddf7ad1cdfacdd2386e16bbfafd1ed4f455`，42项是前序有效证据，本轮执行pytest为0。

## 实际观察与含义

一个真正fresh普通child通过现有生产loader创建guard，无逻辑fixture、无_set或其他guard状态改写。取证accepted，loader仍抛`SavedSuccessorImportUnresolved`、boundary FAULTED/hook inactive、violations=0/fault_kind空；optional/blocked/sentinel/internal为1/1/1/6，NumPy False。P1/actualF open、write、mutation及额外process观察计数全0，内部科学API没有profiler计数证明。

唯一变化是同一`sys.meta_path`容器从4项变6项：

| 顺序 | 导入前 | 导入后 |
|---:|---|---|
| 0 | DistutilsMetaFinder | **pyomo.common.dependencies.DeferredImportCallbackFinder** |
| 1 | BuiltinImporter | 原DistutilsMetaFinder，同一对象 |
| 2 | FrozenImporter | 原BuiltinImporter，同一对象 |
| 3 | PathFinder | 原FrozenImporter，同一对象 |
| 4 | — | 原PathFinder，同一对象 |
| 5 | — | **pyomo.common.deprecation.MovedModuleFinder** |

原四项身份和相对顺序保留，无删除。`path_hooks`与`sys.path`的内容/容器均不变，`path_importer_cache`与`sys.modules`的容器身份也不变。仅保存报告内opaque token，不持久化id地址或完整sys.path/env/module表。

结合已pin的Pyomo实际源码与静态可达路径，两个新增descriptor分别对应dependencies.py:544/549的singleton创建/insert与deprecation.py:665的append。这是静态代码和活体对象descriptor的联合归因；探针没有跟踪具体源码行执行。six链没有被观察为本次变更。

现有guard要求完整machinery不变，与该正常冷路径注册冲突。commit过期已在前序修复；本次private source_raw与caller map匹配、父端前后49 raw pins均一致。boundary报告`source49_bookend_equal=false`由其仅在CLOSED置真的定义产生，不能误报为Source漂移，也不能把private raw匹配提升为完整CLOSED。

## 保存、费用和边界

结果根：`results/tables/staged_rts24_saved_fresh_machinery_diagnostic_v1_non_authoritative/checks_01`。`admission.json`单向引用create-only `registration.json`；父端唯一精确EXE/argv/cwd/env启动有见证，stdout/stderr/result/exit和四helper前后pin保存。`archive.py`实际运行并写`checkpoint.json`，accepted=true，绑定11件归档前本根工件及scope文档。最终本根12文件/104,128B，局部帽16/512KiB满足，未复制Source或导航全文。

| 账 | static秒 | pytest秒 |
|---|---:|---:|
| 前序原账，保持118.8725048/120与353.8217016/420 | 118.8725048 | 353.8217016 |
| 本scope登记 | 0.5880178 | 0 |
| 本scope单次capture | 9.3424691 | 0 |
| 本scope小归档 | 0.5501142 | 0 |
| 本scope合计，帽18/0 | 10.4806011 | 0 |
| 全累计，非原120帽下通过声明 | 129.3531059 | 353.8217016 |

全累计483.1748075s。capture含准备0.1305314s、目标8.6965261s与后置pin/0.5s尾保留；Python最初启动、编辑/独立审查/Git未计，因此不是完整workflow wall。终态peak working set 145,121,280B（约138.4MiB）只是观测，无RAM硬帽/整链资源准入证明。child rc0表示取证完成；生产loader仍未返回adapter。reader/pipe/HANDLE关闭全部有真实记录。

前序9条失败及127文件/8,462,120B的8MiB超帽仍原样保留；本根局部合规不抵消原失败。原始540/420/120未延长或重置，1.1274952s静态余额不搬入新scope。本scope仅对既有失败取证，登记前独立固定18s预算。`predecessor_combined_resource_admission`、`policy_resource_admission`、`cold_acceptance`、actualF/run/resource/formal等全部false。

## 后续具体任务

1. 核Git/进程及本checkpoint，复用当前Source和完整取证；本scope只执行了一次normal取证，已经结束，无现场retry。后续实现另立明确scope，不消耗/修改旧失败根。
2. 为versioned policy设计精确Pyomo迁移：原baseline四对象 → 追加MovedModuleFinder → 前插DeferredImportCallbackFinder的预期路径。中间顺序目前主要有静态来源依据，活体探针只覆盖端点。保持原四身份/相对顺序、固定两个finder来源/类/方法代码/实例域与deferred singleton，保持hooks/path/两个容器门禁。不要在末端直接以实际machinery重拍期望。
3. 写清验证根和可观察范围后再实现。测试需覆盖等值换对象、额外增删、重排、超出允许阶段、cache/modules替换和已观察迁移的回退；任意RAM或无可观察事件的中窗ABA继续未证明，不能承诺现有audit hook能检测所有此类行为。
4. 新Source需精确affected回归及真实normal/caught_effect/blocked_installation，再做小型保存/重开；复用当前证据的失效条件需明确。完整cold与保存尚未闭合前，runtime v2继续UNDECIDED、v3 proposal整体admissible=false。
5. 再推进真实producer/bootstrap、transitive runtime、retained owner/ACK/one-shot permit和F。不得将本次取证对象或closed普通guard转换成真实角色能力。actual F及科学/资源/正式gate始终未开放。

本轮Git仅发布小诊断根、scope/本交接与四导航短prefix；并行论文、文献、绘图和共享导航旧body继续保留。最终commit/远端与工作区状态以实时读回为准。
