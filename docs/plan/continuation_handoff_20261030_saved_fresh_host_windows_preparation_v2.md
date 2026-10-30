# F：host Win32 源码准备与严格重放验收交接

2026-10-30，DRAFT_NONAUTHORITATIVE。从本文件继续，先读 [v1 失败交接](continuation_handoff_20261030_saved_fresh_host_windows_preparation_v1.md)及 [host preentry v1](continuation_handoff_20261030_saved_fresh_host_preentry_v1.md)的具体边界；原八组修补的26/26机制证据保留在 [role v2](continuation_handoff_20261029_saved_fresh_full_context_role_v2.md)。持续推进 goal 保持 active。本检查点新增模拟跨度0h，NFC12未重跑，完整F未启动。

## 当前可接续产物

- [Windows resource source v1](../../experiments/staged_rts24_saved_fresh_host_windows_resources_v1.py)：32701B / `fdc85e80a4ae54a5d794e0204bd3b52d3d2e2ea152cb3f3fec1eefdef999b5f1`。准备了 mapping/mutex、Job-list suspended 创建、PROCESS_INFORMATION 恢复、marker-last、resume/terminate、member generation 和逐资源 issued/witness 清理的函数体。
- [Host preentry v2](../../experiments/staged_rts24_saved_fresh_full_role_host_preentry_v2.py)：35157B / `aa4ef1fd616e4928e24d36c03f2d3148fe92dcb931eae6199d3920dd1f30e9b3`。将独立资源根、六键恢复和未决责任接回已有 context/request/OFFER/ACK、manifest/descriptor/argv/header/binding/release ACK 协议。public constructor、open factory、mechanical issuer全部保持关闭。
- [audit v2](../../experiments/staged_rts24_saved_fresh_host_windows_preparation_audit_v2.py)：10172B / `07b7c1b10fe84882f313082e28ce9f1cd0247e0b1b2f4bed3bb0b6a2dfc1ce7e`。显式保留AST空字段，逐canonical字节重建冻结v1 inspect报告，并严格复用原unit证据。资源 [design v1](staged_deliverability_c_saved_fresh_host_windows_design_v1.md)、原 [scope v1](staged_deliverability_c_saved_fresh_host_windows_scope_v1.md)和后继 [replay scope v2](staged_deliverability_c_saved_fresh_host_windows_replay_scope_v2.md)均冻结。
- [runtime manifest](../../experiments/staged_rts24_saved_fresh_host_windows_replay_runtime_v2.json)：14011B / `c1dd92780cd5908ee30e0e3e08a898d217d55e949ed7c77d0e66d717f7f57be7`。绑定C:\Python314\python.exe、3.14.3、79文件/19870005B；包括71个已加载module对应文件、解析/JSON/hashlib源码、加载的pyd、exe和Python目录DLL。阶段前后核pin，C314目录新加载而未绑定的module拒绝。Windows系统DLL和完整TCB认证仍false。

唯一新行为测试发生于v1：**42/42，0 failure/error/skip，20个具名fault cases**；v2新增unit方法数为0，逐字节复用该记录。v1 unit.exit.json为13198B / `851137544fdd7eb90db17fa63f3e1b32602593a1a99800caba8980b4196fedf3`；raw log6239B / `c1e5abe598ecbcf79980ba6b4d05ddcdea41a169c90f986aa5af92fda1fbd322`，42条ok、终端OK、`Ran 42 tests in 4.837s`。7组ctypes field AST、独立Win64的8个size/10个offset，完整Host私有连接，以及返回异常、重入、generation复用、清理不确定性和已知未决窗口均已覆盖。前驱46/99方法未重跑。

v1 saved因AST空字段默认表示差异被拒绝，随后仅checkpoint；其CP14387B / `cf4d9b5edf15dac5dacc83da2366152eafbf865f0f6ea40dcf7fa5d01d58e6f4`、root7/932397B、17.14258499997959秒和失败均原字节继承。v2严格复现 `_IO/_Startup/_Accounting` 的428→436、1577→1585、705→721B表示差异，完整表示与v1已存摘要精确一致；其余四组不变。六类报告篡改全部拒绝，真实AST内容变更保持可区分，JSON round trip精确。原F合同也与v1登记记录canonical exact相等。没有忽略不一致字段或修改旧记录。

v2 inspect report仍为3052B / `e65c5e75bff6a4e1d2c3b8073aec855db5338e849df1239af66e0cf83d38c8a4`，repair2215B / `811e00589e4fa14a33ce003c55fafb09ea8f0f52affae510d696cc3dfee866fa`。独立只读PRE_SEAL在该有限scope内must_fix_open=[]、official_review=false；fresh核1683 input、355 archive、95 own及79 runtime，1771规范化唯一物理路径、267 input/archive重叠、无missing/mismatch。42项并行工作及NFC12原16文件/1849773B保持；没有official verdict/receipt或production seal。

## 当前唯一账源

[v2 checkpoint](../../results/tables/staged_rts24_saved_fresh_host_windows_preparation_v2_non_authoritative/checkpoint.json)：34577B / `ab980a79488fa414788a49aff112a359871e63632e84d562dcd12b2842f6ce2f`，accepted/accounting_complete/diagnostic_accepted=true；scope仅为 `host_win32_resource_source_and_private_protocol_synthetic_only`。root6/1005148B。

| 阶段 | charge秒 | bytes | SHA256 |
|---|---:|---:|---|
| register | 1.7053688999876613 | 915788 | `911d3f001636d0750f3628435b7c2c29db00df68adc937afea175aa9d379fff8` |
| inspect | 3.401246400011587 | 7113 | `ea72cd2e443948a137a2a9767893dd0bbf7a9bb9d11245c2fb9bff5c143de312` |
| pre_seal | 2.194318599998951 | 19363 | `c6d5344fe34461a52a83bf7998d97512bd40527a781b4baa845e31aa252259cb` |
| saved | 3.458674900000915 | 5274 | `fe917afc193bac6f6c9b328b56d4c9af826f162c4939c67a26c7afaa3ab4ec98` |
| checkpoint | 2.7094803000072716 | 34577 | `ab980a79488fa414788a49aff112a359871e63632e84d562dcd12b2842f6ce2f` |

driver23033B / `44fa81e6e314873d3bec1591417768b6cdf33c7b0354dac9d05608fa9febd462`。本包static13.469089100006386/34秒，阶段帽5/6/10/8/5；无新增unit预算或unit费用。root10files/4MiB、record1MiB、CP预留1MiB/1slot保持。累计static **768.5341269999947**、pytest **366.48897970000326**、unittest **449.31874729998526**，合计 **1584.3418539999832秒**；**62条不接受记录**完整保留。本包无新增拒绝，失败费用没有退款。这些数值是已登记阶段费用，不是协作墙钟或完整F耗时。

当前input **1683/112307379B**、own **95/20127068B**、archive **355/45349680B**。后继先取input1683+root6−driver overlap1=**1688/113289494B**，archive355+root6=**361/46354828B**，再与新own做exact union。本交接在CP后写入，不属于本包登记input；后继使用须显式加入。完整WIP、八组修补、全部失败、原B1–B3/P2七输入、Source49 epoch、NFC12与原42项并行工作继续继承。

## 尚未接通的部分与下一步

Native-return到首次Python标量HANDLE捕获仍OPEN；PROCESS_INFORMATION输出恢复不证明该窗口已关闭。漏观测短命Job member时保持UNRESOLVED，Host尚无接入的completion-port/连续成员观测；瞬时close witness不证明永久防重用。成员数上限1024及保守保留策略尚未获得整个F适用性证据。

当前private tests只去掉两个mechanical首raise，使用fake DLL、合成clock和测试自建ctypes buffer。没有项目Native API、P1读取、Source49模块执行或validation/fixture/target child；控制Python进程和普通文件读取实际发生。未执行Native sampler/Capture1/DRAIN1或连续RSS测量。resource源码准备和静态重放不构成真实host provider、source-auth issuer、owner seal、runtime/TCB或实际entry认证。

1. 继续独立source-authenticated provider/creator准备，绑定真实owner与固定源码。实现manifest/transport/create-only文件provider，并明确外部broker/guardian的持有责任，处理首次HANDLE捕获窗口和未决资源的跨进程寿命；继续保留未知状态。
2. 将acceptance/resume/cancel及broker terminal接入真实协议，使accepted但未release的失败有明确cancel/abort ACK。成员观测与whole-tree quiet也须接入同一寿命协议。
3. 为完整context bytes定义Core manifest/case/helper refs/startup-import profile。Core51目前只有context SHA，现有v2诊断manifest及薄suffix不构成完整role入口；再接Guard2、parent/fresh单次role claim与source launcher。
4. 在真实Native/P1/Source49目标或完整F之前，准备具体失败/停止矩阵、调用次数、整个DAG及wall/RSS/storage预算，按agent.md第9节取得专项授权。普通源码准备和有界静态/单元验证可以继续；不重跑NFC12。

29个执行/科学/生产门仍false：包括physical_host_provider_implemented、source_authenticated_host_issuer、full_role_entry_connected、native_equivalence_verified、native_return_to_publication_window_verified、whole_workflow_budget_admitted、resource_admission、run_authority、actual_F及formal_result。原F仍为双侧独立B/C/E21点h−2..2、五accepted小时、130CAS、19metrics、17targets；原180秒单时钟；P1 reads12500/source-runtime6500；8MiB/64files含四份terminal512KiB/4slots；阶段10/45/40/5/5/15/5/10/15/15/15，成功165秒，失败只用原剩余额度。12159=`2*5055+3*683`与12053=`2*5002+3*683`仅为条件P1算式。Source49 epoch仍`acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`；NFC12 CP21591B / `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`保持。

本轮开始HEAD及remote为`ec6c187f38d3f7d6212fa0b68a136457230bee19`。仅发布本轮Windows源码/fixture/tests、design/scope、完整v1失败与v2后继root、runtime manifest和两份交接；原42项dirty/untracked保留。发布前核Git blob原字节，之后核remote hash、空index与原42项snapshot。实际发布commit以 `git log -1 --format=%H -- docs/plan/continuation_handoff_20261030_saved_fresh_host_windows_preparation_v2.md` 查询；发布不改变任何运行门。
