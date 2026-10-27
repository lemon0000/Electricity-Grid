# B_S完整导入：首次有界诊断未返回

2026-10-28，DRAFT_NONAUTHORITATIVE。承接[真实busy前缀交接](continuation_handoff_20261028_saved_fresh_image_pin_busy_prefix_v1.md)，起点提交`9d8f7a7b92821f39fb496371c7099c510ae51d35`。[本次范围与预算](staged_deliverability_c_saved_fresh_full_import_scope_v1.md)在首次size前固定。root唯一writer，既有独立reviewer只读PRE_SEAL；没有official verdict、production seal或运行授权。宽goal仍active，F尚未完成。

## 本轮结果与边界

独立full helper只改变`diagnostic_import_once`函数body：保留signature、held defaults、primary identity/cause与finally trace，取消固定64的主动停止，让唯一importer正常返回。其余guard、image pin、machinery、ownership、Source49与科学adapter不改。core23只迁移同长度root；probe20新增真实`runtime_preclose`并使用私有v2报告；parent20固定完整成功矩阵。成功目标原为OBSERVED→CLOSED，不授予LIVE。

执行前四项finding均已修复：本地60模块/1097959B的raw pin与精确import-time调用清单；v2顶层与七字段guard exact keyset；至少一对完整graph；RSS只能是非负整数加error=None或peak=None加有界非空error。FunctionDef仅将body替换Pass后比较，覆盖全部header字段。未知源码、alias或computed调用变化拒绝；既有清单中的路径解析、字面量split、字段类型表与类型提示处理已读回。清单只证明已pin本地source的显式调用边界，外部package/native行为未认证。

size、register、六项unit、PRE_SEAL、startup、profile全部通过。命令为**29994/30000 UTF16单位**，仅余6单位；decoded payload的原位置AST、CodeType与字节变换均通过。六项unit为合成方法/协议验证，覆盖wrapper、异常链、schema、graph、RSS与权限字段漂移，不能代替真实完整链。

**唯一full import未完成，`full_import.exit.json accepted=false`。** 外层charge **7.515819500004/8s**；内部父端case cap **7.138348000000406s**，charge **6.651821999999811s**，`bounded_drain.killed=true`、child exit1。stdout为空，stderr完整790B，只有15对graph及`loader_ready`、`before_adapter_import`两个stage，没有`adapter_import_returned`。原receipt primary为`AssertionError:`，没有保存drain reason字面值；依据已pin drain代码中唯一kill分支，结合无overflow/truncation/reader error，可推断为内部deadline到期，不能把原primary改写成TimeoutError。

父端process HANDLE、stdin、pipes、writer/readers均关闭/终态，cleanup、reader_errors和writer_errors为空，streams未截断。child终态报告缺失，self HANDLE close次数、runtime/boundary/resource最终phase与异常链均**unknown**；不能沿用固定64前驱的close[1,1]或UNRESOLVED/FAULTED。没有OBSERVED证据，也没有import profile、saved或完整成功矩阵。

direct child peak working set **81625088B = 77.84375MiB**，GetProcessMemoryInfo error=None，采样发生于父端HANDLE关闭前。这只是本次已终止child的观测，不证明整链RAM上限或资源准入。startup child exit0，peak38936576B。

stderr中15对graph计时合计 **0.6231119000003673s**；首graph时标54939.9475268，到before_adapter_import时标54941.0059761，相差 **1.058449299998756s**。该差值不是冷启动总wall，也不是import耗时。import内部没有阶段采样，具体函数、open数量、cache增长与耗时分布仍未知，不能断言超时发生在NumPy、Pyomo、某个guard或某个native调用。

## 预算与不可变入口

root：`results/tables/staged_rts24_saved_fresh_ful_v1_non_authoritative`，**23文件/874083B**，上限30文件/4MiB。checkpoint写后不再往root追加或改写文件。执行1个unit child、2个串行cold child（startup与唯一full）；没有重试、延长预算、模型实验、P1读取或角色/F运行。终态后仅语言服务器Python仍在运行。

| 阶段 | charge秒 | 终态 |
|---|---:|---|
| size | 0.9942694999990636 | accepted |
| register | 0.998521300003631 | accepted |
| 六项unit | 1.9710476000036579 | accepted，6/6 |
| PRE_SEAL | 1.1296585999953095 | accepted，非official |
| startup | 1.6908891999992193 | accepted |
| profile | 1.0016383000038331 | accepted |
| full import | 7.515819500004 | not accepted |
| rejection checkpoint | 0.6940774999966379 | accepted，仅metadata |

本轮static **14.024873900001694/22s**，unit **1.9710476000036579/5s**，总 **15.995921500005352/27s**，独立帽之间不借用。未用额度不重置历史费用。checkpoint的`accepted=true`只表示拒绝元数据保全，`acceptance_scope=rejection_metadata_only`、`diagnostic_accepted=false`。

承接前驱全账，累计static **268.0192162000051**、pytest **366.48897970000326**、unittest **71.44163690000642**，总 **705.9498328000147s**；未接受记录 **27→28**。编辑、审查、Git、Python初始启动和最终记录写入沿原口径不计capture，这不是完整wall，也没有模拟小时推进。失败charge全额保留。

先读本root `checkpoint.json`、`registration.json`、`size_admission.json`、`pre_seal_findings.json`、`unittest_report.json`、各exit、`probe_import_discovery.receipt.json`。原始stdout/stderr以base64及pin留在receipt；checkpoint绑定23文件中的其余22份。Source49 epoch保持 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**，全部49份raw不变，旧失败与前驱root原样保留。

## 下一步

当前堵点仍为**完整B_S import的性能定位与闭合**。先复用固定64与本次阶段证据，审查import-time路径、guard/缓存/来源验证调用倍数和安全优化条件。下一诊断须单独固定有依据的有限规模、采样点、次数、存储、预算与关闭预留，并建立独立successor；不得直接重跑本CLI或把8s顺延。现有日志不足以证明具体性能原因，完整F工期仍不可可靠估算。

完整import以后仍需独立OBSERVED profile、正常LIVE及故障矩阵、真实producer/retained owner/Job/bootstrap、ACK/issuer/permit、quiet/返回与父端采用。E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部保持false。本轮只推进并保存开发诊断，没有科学结果或资源准入结论。

39项并行文稿/图件/文献dirty保留；Git只同步本轮已审scope与四导航新增段，导航原工作区正文保持。远端提交号与scope clean状态以发布后的实时读回为准。
