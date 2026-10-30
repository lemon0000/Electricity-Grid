# F：outer host 协议与 suspended 顺序验证交接

2026-10-30，DRAFT_NONAUTHORITATIVE。持续推进goal保持active。承接[endpoint v4](continuation_handoff_20261030_saved_fresh_endpoint_preparation_v4.md)；用户最初八组role修补的26/26机制证据见[role v2](continuation_handoff_20261029_saved_fresh_full_context_role_v2.md)。本检查点推进outer host协议与寿命控制流，新增模拟跨度0h，NFC12未重跑，完整F未启动。

## 本步实际产物

- [host preentry v1](../../experiments/staged_rts24_saved_fresh_full_role_host_preentry_v1.py)：33420B / `aad8178243714d0ceef51592d1eec1c33c6dca4ae3907aa8c93df7cb0fe6f922`。完整context/request/OFFER/ACK、manifest/descriptor/quoted argv/header/binding/release ACK形成单向DAG。outer controller只用原prepare10秒；parent/fresh仍需独立source launcher和阶段reservation。
- 操作锁和effect前后检查保留吞掉的重入错误；artifact image、resource escrow、acquisitions与close-issued账本分别持有。partial acquire错误不覆盖primary，close失败继续其他可关闭资源；Job或child identity/quiet不明时保留全部Native资源。accepted binding后超时保留DONE事实并停止resume，真实broker cancellation/abort ACK仍OPEN。
- manifest是按nonce create-only保留的forensic artifact，占1file/最多131072B；发布、receipt或readback不确定均保留UNCERTAIN及路径reservation。它不属于删除清理。物理create-only/identity/nonce排他仍待真实provider验证。
- [design](staged_deliverability_c_saved_fresh_host_preentry_design_v1.md)、[scope](staged_deliverability_c_saved_fresh_host_preentry_scope_v1.md)、[audit](../../experiments/staged_rts24_saved_fresh_host_preentry_audit_v1.py)与[46方法](../../tests/test_staged_rts24_saved_fresh_full_role_host_preentry_v1.py)均由registration冻结。Core51、薄suffix、role v7及前驱99方法原字节保持；本轮未重跑99方法。

Host构造、open_full_role_host、原mechanical issuer继续关闭。真实host effect provider尚未实现。本步仅接受 `outer_host_protocol_and_suspended_order_synthetic_only`，不能称真实host/完整角色接通。

## 验证和边界

唯一普通unit为46/46、0failure/0error/0skip，contract_errors为空；23个具名fault cases。原log6595B / `95f77ca42e2043414054b5428b7636c8f8d55da25f2fbed7b3a355d2cc9e5092`，46条ok，`Ran 46 tests in 5.008s`。该5.008秒是测试器内部时间，包unit阶段含输入核验等为7.691527600007248秒。

覆盖完整数据关联、quoted UTF16含NUL容量、独立header framing oracle、未修改Core51 endpoint消费host header，以及部分acquisition、publication前后/非法receipt/readback、同数值view/HANDLE分域、1025 member拒绝、缺Job/identity、原时钟倒退/过期、external acceptance拒绝或超时、resume/terminate/close issued uncertainty、吞重入、artifact漂移和原错误重复抛出。

全部在控制进程的私有copy和synthetic filesystem/context/Native叶执行；仅移除mechanical首raise。完整context bytes为synthetic，49 pins只来自保存记录；project Native、P1读取、Source49模块执行及validation/fixture/target child均0。没有Capture1/DRAIN1/Native sampler或连续RSS测量。Python控制进程本身不是“零进程”。

check_manifest/check_transport在fixture分别只核context SHA与bytes equality；Core51测试只证明header/endpoint协议消费，不证明完整manifest、实际OS argv/profile、transport/payload等价、context载入或Guard2。未来source provider、Native acquisition return-publication窗口及协调execution-anchor破坏仍OPEN。acceptance DONE后失败尚无真实跨进程cancel/abort ACK。

独立只读PRE_SEAL在本有限scope内must_fix_open=[]，official_review=false。fresh核1578 input与341 archive，1666规范化物理唯一路径，0missing/mismatch；own12全匹配；原42项并行snapshot全匹配，NFC12原16文件/1849773B全匹配。原NFC12 CP仍21591B / `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`。没有official verdict/receipt、production seal或运行授权。

## 当前唯一账源

[checkpoint](../../results/tables/staged_rts24_saved_fresh_host_preentry_v1_non_authoritative/checkpoint.json)：12944B / `c2700bd2fa6f9e182753115ad176f64410bcdfc7fd846f5151adfea49df930bf`，accepted/accounting_complete/diagnostic_accepted=true，root7/915420B。

| 阶段 | charge秒 | bytes | SHA256 |
|---|---:|---:|---|
| register | 1.0953250999882584 | 854577 | `206db7e1394e4561208ea2798d083332d05077ea5ea02c2a39537235bd08fcea` |
| inspect | 2.2708516999991843 | 3039 | `91d13650e2078eaa5623f18083e434336febc92c44922148a4ddd7ea27e58e66` |
| unit | 7.691527600007248 | 13472 | `4a0595eaeda5458567c6619ce1c4466819b8b8a611af4a401edec7060f6bc190` |
| pre_seal | 2.641425800000434 | 7148 | `470d37afe208cfe9037ba0bfde811cf132b18a1cb24f2fefffc4107a75199732` |
| saved | 2.2850407999940217 | 4105 | `4d394d6c9cd2ed8d594eb7449e28872bbc6e358edd5a270f7b8a59d2ca01e181` |
| checkpoint | 1.2368709999864222 | 12944 | `c2700bd2fa6f9e182753115ad176f64410bcdfc7fd846f5151adfea49df930bf` |

driver20135B / `0151831ee05638cce387397df08ef9324a8745d47cccc2361c5c7911ab1b6178`。阶段帽5/6/35/10/8/5，static34+unittest35=69秒；包实际17.22104199997557秒。root10files/4MiB、record1MiB、CP预留1MiB/1slot保持。首次register冻结，首拒仅checkpoint；本包没有新增不接受阶段。

累计static **744.9687038000004**、pytest **366.48897970000326**、unittest **442.27249639999354**，合计 **1553.7301798999972秒**，**61条不接受记录**全部保留、不退款。这是已登记阶段费用，不是协作墙钟或完整F耗时。

当前input **1578/90434661B**，own **12/285949B**，archive **341/43501863B**。下一包先取input1578+root7−driver overlap1=**1584/91329946B**，archive341+root7=**348/44417283B**，再与新own exact union。本文不在本包input map，后继若使用须显式纳入。完整WIP、八组修补、全部失败、B1–B3/P2原七输入、Source49 epoch、NFC12原16及原42项并行工作继续继承。

## 下一步

1. 实现独立source-authenticated host creator/provider：绑定固定CodeType/TCB与真实外部root；提供create-only文件/endpoint、Job-list suspended owner、PID/creation/OS argv、header marker-last与readback，以及逐HANDLE issued/witness清理。当前effects tuple只属于关闭issuer后的准备接口，不得把private test copy作生产入口。
2. 把acceptance/resume/cancel及broker terminal放入真实协议，使已接受但未release的失败得到跨进程确认。保留原180秒及阶段/terminal reserve，不由每个role重新开prepare10秒或cleanup15秒。
3. 为完整context bytes载入定义新的Core manifest/case、helper refs及startup/import profiles。Core51只有context SHA；当前host仍构造其v2诊断manifest，并不因此具备完整role入口。随后接Namespace/Guard2、parent/fresh单次role claim、source-specific launcher与inner/outer quiet。
4. 准备具体Native失败/停止矩阵、次数、整个DAG调用量与wall/RSS/storage预算；按agent.md第9节取得专项授权后方可运行真实Native/P1/Source49目标或完整F。普通源码准备与单元验证可继续，不重跑NFC12。

原F仍为双侧独立B/C/E21点（h−2..2）、五accepted小时、130CAS、19metrics、17targets、180秒；P1读12500/source-runtime6500和8MiB/64files含四份terminal512KiB/4slots保持。stage仍为10/45/40/5/5/15/5/10/15/15/15，成功165秒，失败只用原剩余额度。12159=`2*5055+3*683`及12053=`2*5002+3*683`只是条件P1算式，不是source总读量或整链admission。

本轮开始HEAD为`03accac50dc1e45fc28228dda5c3400dcbb90e6c`。只发布本轮新源码/测试/design/scope、完整root与本文，保留原42项无关改动；发布前核Git blob原字节，之后核remote hash、空index及42项snapshot。实际发布commit用 `git log -1 --format=%H -- docs/plan/continuation_handoff_20261030_saved_fresh_host_preentry_v1.md` 查询。
