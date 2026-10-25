2026-10-25最终终态：**静态设计通过，完整保存验收未通过**。六条charge合计27.9873943/90s：前四条exit0，saved_05与terminal_06均exit1/accepted=false；末次package prospective检查为true，最终14files/72,916B，但仍被前序`partition(b'\n\n')`标题段检查拒绝。迁移遗漏了标题后的空行。达到6次上限后停止，没有第七次；预算余时不授予新attempt。原main31/1,135,236B与failed包14文件、全部原记录/两epoch/两个失败checker均保持。全量复核未闭合，不能将前序282/8的保存记录称为本轮完整archive重放通过。详细pins与下一步见[checkpoint_status.json](checkpoint_status.json)。本段是终态后的文档状态记录，未运行新验证。

10域/59节点/21项当前静态结构结果保持，26runtime faults仍UNRUN。下一步为独立mechanical successor固定范围/预算，修复双LF标题段和body suffix兼容后重放；actual F与所有科学、资源、正式门禁不变。

以下为 finalizer_04 冻结的预执行正文；其中保存复核相关表述不构成终态通过证据，终态以本页顶部和 checkpoint_status.json 为准。

# 三角色上游合同开发记录

2026-10-25，DRAFT_NONAUTHORITATIVE。范围以[执行合同](../../../docs/plan/staged_deliverability_c_saved_fresh_upstream_contract_scope_budget_v1.md)为准，[交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_upstream_contract.md)记录下一步。起始HEAD/origin `f3b4717973557b04e558485267431cc32556b5b5`。root唯一writer，既有独立只读PRE_SEAL；无production seal/review receipt/actual F。

本轮形成一个10域registry、59节点runtime展开图、独立规格hash图、三角色fixed argv grammar、固定模板和未来26项runtime fault matrix。每域固定producer/consumer、schema literal、字段类型及编码帽，跨进程数据不能转为同进程capability。尤其拆除了packet↔argv、packet↔descriptor及packet↔future owner identity循环，复用post-create StageChannel header。第一次create-only allocation前sticky消费原attempt，失败保留原reservation与cleanup对象，不换nonce重试。

当前revision_02独立设计oracle检查通过，21项RAM设计负例均拒绝。它检查schema/角色闭集、数据/能力边及macro expansion、两图拓扑、metadata恒false和最大合法canonical编码。PRE_SEAL修正了controller错误依赖RoleStore reservation、descriptor缺生产字段、固定SHA未有equality、producer侧capability归属、archive导航suffix，以及容量组合/helper snapshot覆盖。controller现用broker-local attempt，parent/fresh沿用reservation；descriptor完整保留production阶段、时钟与资源值。它不校验实际context/request/ACK/producer/clock相等，不发行任何真实对象。生产data validator与runtime cross-field checks未实现；READY/START/offer、entry header/failure、local projections/reservation commitment及startup仍待独立合同。26个runtime fault matrix状态全部UNRUN。

| domain | controller上界B | parent上界B | fresh上界B | payload帽B |
|---|---:|---:|---:|---:|
| permit-binding | 1431 | 1668 | 1649 | 4096 |
| entry-packet | 7356 | 7593 | 7574 | 32768 |
| descriptor | 847 | 743 | 662 | 3072 |

ACK上界1081B≤3072B，3072+条件frame上界363≤4096；entry与binding拟定raw帽为36864/4608B，各另加44B physical overhead。按旧exact stage header shape，descriptor使用3072B最大帽时总3385+44≤4096。path类型以canonical单值≤4096B约束，escaping计入。新transport的header、failure记录等尚未固定，上述逐字段求和不构成整条wire/RSS admission。

`baseline_01` charge4.455939s，历史`design_02`1.925407s，当前`design_03`4.367276s，均terminal0、stderr空，总10.748621s。后续finalizer和两次saved oracle纳入同一90s累计账，原stdout/stderr/exit保留；原余量已用于design_03，exact六次之后不再追加。单次capture charge=observed pre/post-pin window+0.25s未实测尾部reserve，Python启动/编辑/审查/Git不在此窗口。不能把它解释为actual F或全workflow墙钟上界。

旧15项结构结果属于前一draft epoch，不作为当前21项证据。旧4JSON/原合同exact bytes以base64归档，old/new全部helper snapshots逐pin核；旧JSON archive未由design_02执行记录pin，historical_design_archive_execution_binding_proved=false，只作历史恢复材料。revision manifest绑定旧baseline/archive和当前helper/合同；design_03以后record另pin当前4JSON。没有改写旧record或把相同路径的新字节追认为旧执行结果。

4058前序路径和Source49在每次capture前后逐pin复核。ENTRY/tests及scientific adapter无修改；source epoch仍`00ef897eb83d55f79491804cc49ee5302d766dd533ee3d8615ffff84b6a1e83a`。保存oracle按exact SHA装载前序stdlib archive，复核冻结282节点/8 ordinary cold probes/P1全683；本轮没有重跑pytest或启动cold/role/scientific/native/Job/OwnedChild，新增模拟小时0。所有历史、失败、冻结证据原地保留。

execution freeze后不再写checks_01；final_package_01只含独立saved oracle、execution inventory/support和机械原记录。execution≤32files/2MiB，package≤16files/1MiB，新文档≤4files/1MiB。saved oracle不能自证尚未发布的本次exit，后继record和最终Git blob读回承接。最终diff/link/hash/process与独立PRE_SEAL审查完成后按授权精确同步Git。actual fresh/最终父端采用、full input/runtime/hold、科学采用、资源与正式门禁全部未开放。
