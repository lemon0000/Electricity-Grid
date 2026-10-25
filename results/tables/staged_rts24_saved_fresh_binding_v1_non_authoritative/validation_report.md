# F saved 子角色绑定接口开发验证

2026-10-25，DRAFT_NONAUTHORITATIVE。起始HEAD `bdeebb784575824742f89b76be7e11ad5a730a1c`。接续[文件入口交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_entry.md)，按[本轮合同](../../../docs/plan/staged_deliverability_c_saved_fresh_binding_development_contract_v1.md)开发。root唯一writer，独立只读PRE_SEAL；无official verdict、receipt、seal或运行许可。

本轮实现实际saved context的子角色绑定接口和构造输入。**实际saved文件入口、owner、watcher、trusted supervise尚未接通；公共saved CLI仍exit 1。** 没有创建真实OUTPUT或其父目录，没有B/C/E科学重放、新fresh或solver/native求解；新增模拟小时为0。

## 接口与拒绝边界

`argv_for`现为唯一saved parent/fresh canonical builder，固定`--saved-entry`、role、context path/SHA、tree SHA、channel name/nonce。input/output从context推导，descriptor从role推导。supervise因缺少saved trusted-invocation绑定而拒绝。原设计模板和旧源码snapshot保持。

独立`SavedFileBootstrap`冻结raw context、role/tree/transport、argv/orig_argv、main/alias/search path、ENTRY bytes/file identity/完整父链、executable bytes/identity和受控环境。RoleStore初始化核同一raw/role/tree，protected check和execution_context另核同一Open-only writer及header/descriptor。ordinary与saved域双向拒绝混用，单有schema、argv或全局对象不能进入科学分支。

`saved_owner_inputs`只接exact held RoleStore、同一原reservation和unbound channel；tree/context/writer由store派生，不提供factory/callback/descriptor/argv/tree override。生成数据即消费reservation，原开始时刻保留；最后store检查后重新核context/source/EXE/环境和deadline，之后纯内存提交。后续check同样过期失效。数据不可序列化，无launch方法，固定`native_owner_constructed=false/run_authority=false`。当前只有parent→fresh的数据路径有单位正例，controller→parent还依赖未实现的saved supervise能力。

环境同时核完整受控键集合和实际键值，捕获归一化会掩盖的六个forced键。ENTRY同字节换identity及父链漂移拒绝；未声称原子文件系统快照或覆盖未观察ABA。proof/构造image实际受16KiB帽限制，未嵌入完整context/683 pins/caller image，未增加17 targets。

## 终态检查与预算

全部pytest尝试累计 **238.315s＜240s**，包含失败、早epoch及超时；collection/静态保存核验另按60s，总帽300s。runner在每组启动前要求其cap落在剩余240s内。为避免重复import，最后7个尚未运行的角色节点合并一次执行，cap21.4s；原actor阶段/caps保持，无actor自动重试。

| 当前相同源码epoch终态组 | 节点 | wall s | 结果 |
|---|---:|---:|---|
| binding_commit_08 | 9 | 17.297 | 通过 |
| binding_reservation_09 | 12 | 20.625 | 通过 |
| binding_rest_10 | 7 | 12.610 | 通过 |
| role_critical_11 | 12 | 9.000 | 通过 |
| legacy_15 | 4 | 11.938 | 通过 |
| role_graph_a_12 | 8 | 26.829 | 通过 |
| role_graph_bc_13 | 7 | 19.891 | 通过 |

共 **59个唯一节点**：28个saved绑定单位检查、12个RoleStore关键回归、4个受影响接口检查、15个完整ordinary角色矩阵。15个角色节点分组全终态通过，闭合了当前epoch的整组角色回归缺口；旧45s超时记录仍保持原状态。当前normal角色图的父/子完整quiet、成员嵌套及process record由独立保存oracle复核。

新增单位测试共77节点，最终epoch只执行上述28个，**未声称全部77当前通过**；完整26个旧role units仅选12个相关节点，normal external invocation计划未执行。早epoch的4项smoke、9项affected及22/16/13项通过组只说明各自冻结字节的事实，不计当前59。

保留非通过attempt：binding_units_01为4 pass/56 setup errors，25.766s，原因是实际OUTPUT父目录不存在；binding_owner_07触30s帽，实际30.015s，未取得整组终态，不计通过。其余早epoch源/日志全部保留。PRE_SEAL逐项发现并修复store/reservation、域混用、ENTRY identity、deadline/runtime、环境键集合和consume窗口问题；最终静态复核无必修code finding，不能等同于全部pre-seal验收或seal readiness。

单位正例显式替代main/flags/preimports、输出父目录identity、output tree与transport/native边界；其中P1锚/SF49/caller capture为只读真实数据。`SAVED_BINDING_FIXTURE`保留logical标记和context pin。该证据不证明实际saved进程、物理输出目录、OS命令行或完整runtime closure。terminal image冲突后的直接单位检查已写入并在早epoch组通过，未计当前59；真实root-exit残留conhost成功窗口仍OPEN，saved标签不获得ordinary cache例外。

## 保存核验及下一步

14个ordinary角色图从原stdout派生为197 archive entries，包括169份原文件字节和14份context projection；projection仅保留原pin及省略environment的投影，不能当原context消费。历史generic stage/guard87仅在原AST/闭集域复用，不计当前59，也不证明saved watcher。

2,382旧路径、三导航原正文、P1全683文件/2,950,863B、科学adapter、原scope-budget、旧guard/outer与SF49集合保持。使用[新保存检查](checks_01/saved_checks.py)核字节、snapshot、原始日志派生及process witness；它不执行或授权F。

首次保存核验错误地从成功返回读取其未包含的context SHA，exit 1及helper snapshot保留；随后改用原stdout归档的context原字节pin绑定process record，不以projection或重建context代替原SHA。

下一步先在冻结源码上为其余49个新单位节点固定有限预算，再实现独立saved constructor/watcher与trusted supervise，保持原一次parent/一次fresh、零solver/重试、40+5+5/180s。实际调用清单、最大合法context/四record编码、昂贵失败/发布费用、arming/host最终I/O硬中断、完整wall/RAM/storage仍待闭合。局部saved verified、F_launch_admitted、整包science/resource/formal/public P2全false。详见[新交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_binding.md)。
