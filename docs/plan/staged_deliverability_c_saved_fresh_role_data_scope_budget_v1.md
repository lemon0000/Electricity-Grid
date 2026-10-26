# C：三角色独立声明与 data-only 校验接口

当前有效预算与恢复顺序以文末两次恢复段和本段为准；前文99.7533s、初始group caps与预留表属于当时尚未执行的历史计划。最终测试已完成：480目标节点、12成功组，pytest charge242.7843532s（含role_1失败）；static在finalizer前45.5662806s，后续caps12+22+22，最坏101.5662806/120。所有原失败与helper epoch继续保留。

2026-10-25，DRAFT_NONAUTHORITATIVE，起始HEAD/origin `e4e02343ffceb3605fe839dbe6646ea7fba9cbd1`。接续[机械archive交接](continuation_handoff_20261025_saved_fresh_upstream_archive.md)。root唯一writer，既有独立只读PRE_SEAL；无seal/official receipt/run authority。采用已读karpathy-guidelines，范围限ENTRY追加接口、原测试文件新增有意义的行为测试，以及独立开发证据。旧函数/类AST、scientific adapter、Source49集合/其他47路径、P1与历史/失败工件保留。

## 固定 API 与三类结果

新增 `validate_saved_controller_entry_data`、`validate_saved_parent_entry_data`、`validate_saved_fresh_entry_data` 三个固定role入口；不增加公共role字符串工厂或CLI运行分支。三者读取exact bytes packet/permit-binding/descriptor、独立publication/tree/transport/basis声明、固定registry/templates和caller声明now。context_data必须为原exact `SavedSuccessorDataCheck`。parent另需exact controller data对象，fresh另需exact parent data对象及各自独立的bootstrap/G0或hold/store/issuer原声明字节。

冻结10-schema仍以21981B、SHA `d5e467a761ea5d50c939f9b76fd702775381341996c3a0aaf5e563025a62520b` 的registry为唯一数据域；templates为2231B、SHA `36cff2e3fa3a11da0d6a2de7a088e8be94d528a1f2a2c33e14a88f03d57a0d0a`。解析前核raw cap与固定pin，逐项核closed keys、exact bool/int/float/literal、SHA、pin、receipt、Windows path/name及fixed artifact equalities。每角色只接受自己的binding/packet/descriptor；controller另校ACK。packet引用binding SHA，descriptor引用packet/binding SHA；不改变无环方向，也不让数据摘要成为permit。

返回 `SavedControllerEntryData`、`SavedParentEntryData`、`SavedFreshEntryData` 三个不同exact immutable type。普通constructor、subclass与pickle拒绝。结果强持原raw、同一context对象、原upstream对象、其id/commit和creator `(os.getpid(), get_ident())`，自身commit包含object id；entry重复核对象/creator/commit。parent/fresh的独立basis固定预期context对象id/commit和upstream role对象id/commit/creator；同字节重建、换context对象、异role-result creator均拒绝。旧context DataCheck本身没有creator字段，本轮不证明它的原创建线程；context_origin_creator_verified=false。这只是同进程data provenance，os.getpid/thread id不认证任何producer、HANDLE或kernel creation identity。

object id/creator引用属于各调用进程本地的独立basis，不进入冻结wire packet，也不跨进程传递这些结果对象。未来child须从独立raw/transcript和自身观察建立新的本地data链；实际上游capability、外部retained owner/Job与bootstrap另按真实角色协议验证。本轮不将三个本地data对象称为三个actor已连接。

## 独立 development declarations

除原10-schema外，本轮另定义21个closed development declaration schema：publication1、transport3、role basis3、local episode3、mailbox-header/offer/broker-ACK各1、controller向parent的4项及parent向fresh的4项projection。稳定role tree另是原`_role_tree`格式的bounded canonical list image，不混入21 schema计数。新schema不修改冻结registry，也不是生产wire/header协议。

publication绑定context/request SHA、broker声明identity/stage nonce、context路径/receipt/root目录链、tree pin及声明时刻。tree含固定六目录链和context identity，逐链与publication/root/receipt一致；只校声明，不访问文件系统。transport分别固定role、context/request、entry/stage name/nonce与caller independently held transport数据。basis分别固定producer identity、permit nonce、context/upstream对象引用、原local episode及独立projection pins。

每个projection按固定schema/producer/consumer/context/request/stage nonce、相关upstream packet/binding SHA和declared_at分域；own raw SHA只放独立basis pin，避免自哈希环。mailbox header在context前，其context/packet/binding SHA固定None；它绑定request、host/broker identity、host nonce、mailbox name/layout与broker stage nonce。offer和broker-ACK在context后，仍不引用未来controller packet/binding。parent/fresh的四projection引用前一exact data对象中已定稿的packet/binding/stage nonce，不引用将来的下游packet。G0/hold等仅为bounded declaration摘要，不替代科学hold或actual capability。

## 声明时序与 deadline

controller严格核 `invocation_started ≤ header_declared ≤ context_published ≤ tree_declared ≤ offer_declared ≤ ACK_declared ≤ broker_ACK_declared ≤ original_attempt_started ≤ now`。parent核 `controller_data.now ≤ bootstrap ≤ G0 ≤ store ≤ issuer ≤ original_parent_reservation_started ≤ now`；fresh对应 `parent_data.now ≤ bootstrap ≤ parent_hold ≤ store ≤ issuer ≤ original_fresh_reservation_started ≤ now`。所有声明继承同一invocation start/deadline；context/request/ACK及publication、upstream链均绑定相同原字节/对象。

local episode为三种不同schema，controller使用attempt，parent/fresh使用reservation；其nonce/start/deadline与候选packet/binding及独立basis逐项一致。production总帽controller180/parent125/fresh50秒，tail分别10/15/10秒。令s为原invocation start、u为原local start、D为原invocation deadline：local deadline=`min(D,u+total)`；active=`min(s+active_offset,D,local_deadline-tail)`，closed=`min(s+closed_offset,D,local_deadline)`，offset分别155/165、110/125、80/90。要求u<active≤closed≤D且now处于原local start到active之间，不重置原episode或新增失败秒数。now仅是caller float声明，不读时钟、不证明实际未过期或执行deadline。

status允许data_only/declared一致性为true；full projection semantics、producer capability、consumer authorization、wire/header/transport semantics、FS/kernel/clock/physical expiry、reservation消费、permit/owner/Job、full P1/runtime及run/F/科学/资源/正式gates全部false。旧RoleStore/FileBootstrap/SavedOwnerInputs/issuer/constructor继续exact拒绝这些对象。

## 测试、预算与证据

总普通预算480s：全部pytest attempt≤360s，baseline/prepare/collection/admission/静态/保存≤120s；单目标≤45s。开测前collection固定exact nodeids、当前Source epoch、互斥组与每组帽，总组帽≤320s，至少40s仅作失败余量，不扩大实现或运行真实角色。重跑前序282相关节点，不把旧epoch通过继承为当前结果；新增测试覆盖三role正例、closed shapes/类型/caps/字节、声明因果、同字节换对象/creator/context、链/两侧同步篡改与独立basis不变、所有commit字段、默认拒绝域及零FS/clock/Native/模型调用。

collection hook只保留原282已审nodeids及本轮test_saved_role_data_节点。其他旧节点必须属于baseline原test AST中的既有函数并记录legacy_deselected；未知新函数拒绝。新增还含normal/两流溢出/timeout/reader-error/Popen-failure六个普通capture故障逻辑节点。admission要求collection exact=原282+新198=480，再锁组与当前Source epoch；排除旧未选节点不扩大到其native/owner路径。

baseline_01原捕获使用当时wrapper，其已知短输出按原record保留。collection以后wrapper双reader固定stdout262144B/stderr32768B、4096B读块；溢出或reader错误触发direct-child kill/wait，timeout同样保留primary分类。记录observed/truncated、reader终态、pipe关闭与cleanup；未终态不跨线程强关pipe，也不宣称Job quiet。写log之前核prospective raw/exit库存，启动前预留最大两流/64KiB record与bounded metadata空间；metadata每次≤1MiB（admission≤256KiB）。超流只保留明确标截断的有界prefix，不把它称完整raw。目录超帽不先写超量输出；清理未决使capture失败，原F/资源门禁不变。

Popen构造异常也生成accepted=false/sentinel -3/popen_error记录并计费，child_created=false表示未取得Popen对象，不认证OS创建回滚。prospective库存不足而未保留raw时，记录discarded stdout/stderr pin和observed length、raw_retained=false，保留输出身份与明确失败分类。

collection_02在导入完成前因wrapper timeout终态失败：target7.2914982s、charge10.4427467s，stdout/stderr空、cleanup=[]、reader/pipes终态。它不建立任何节点通过。原record/helper与当时scope raw保存；static已耗14.7532966s。新独立label collection_retry_04在剩余原120s内cap20，不改总预算；admission只读其成功harness并核旧失败pin/同Source epoch。后续最大cap20+5+10+25+25=85，已用加全部后续≤99.7533s。

为避免重复冷导入，将原data_smoke/self_smoke/self_rest/direct_compare四组exact并集并为legacy_fast(cap24)，保留全部nodeids且原四label从本轮groups移除。其旧target合计19.517s只作预算依据；当前需重新通过，若同进程fixture交互失败则完整保留，不拆回继承。当前其他旧组cap为binding42/data_a26/data_b25/expectation_a40/expectation_b32/source_expectation25，新smoke25+四新组各20；总319≤320，pytest360内保留41s失败余量，单组≤45。以上均在本轮首个pytest前确定，未缩减节点或科研边界。

fixture独立stdlib生成，不import validator/helper；只读保存P1/固定spec/合同和真实Source pins，producer/identity/time/projection明确为development声明。pytest沿用已固定NumPy lscpu精确阻断与OwnedChild constructor/P1/actual写guard；这不是生产NumPy政策，不证明任意native副作用不存在。普通单元测试不构成actual F或科学采用。

首次baseline在ENTRY/tests编辑前保存旧raw/Source49与全部前序路径；实现后保留实际source/helper执行字节snapshot、raw stdout/stderr/exit和完整账，运行时不编辑文件。Source49中仅ENTRY/tests可变，其他47及全部科学src定义/旧定义AST和P1全683复核。static普通目标预留baseline≤15s、prepare≤10s、collection≤12s、admission≤5s、finalizer≤10s、saved/terminal各≤25s，共102s，剩18s诊断余量；所有失败照计，不延长总帽。

新root `results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative`，checks_01≤160files/12MiB，final_package_01≤24files/2MiB，组合≤184files/14MiB；三新文档≤1MiB，终态JSON≤64KiB。原F8MiB/64files/17targets不变，以上逻辑帽不构成RAM/RSS/实际磁盘准入。保存oracle不import当前ENTRY/helpers，仅核固定snapshot与hash绑定的前序stdlib archive；当前CLI严格Source/nav，future archive漂移不继承current节点。导航必须保留原header双LF与完整旧body suffix。

完成独立PRE_SEAL、针对性/相关回归、hash/diff/link/process核验后按既有授权精确commit/push、remote读回/空porcelain。宽goal继续active，下一步真正bootstrap/producer/owner及完整runtime机制仍依各自合同；actual fresh/最终父端采用、资源/科学/正式门禁保持关闭。

## admission 失败后的原预算内恢复

admission_03 原 cap5 失败并保留：pre/post bookends 导致 charge15.5526346s，target 仅获0.01s，0.0646542s后由wrapper kill/wait，stdout/stderr空、reader/pipes终态、cleanup=[]、未生成admission.json。static累计41.0219193/120s。不得把这次失败当作admission成功。

独立 admission_retry_07 cap20 绑定旧失败record pin及相同Source epoch，仍锁原480节点和pytest319/360组预算。余下finalizer cap12、saved/terminal各22，总后续cap76，含已费最多117.0219193/120；不延长120/360/480总预算。wrapper记录preparation_seconds；prep耗尽可用窗口时不启动目标，保存preparation_budget_exhausted/accepted=false并照计真实charge。该机制不能给文件I/O或完整workflow提供硬停止证明。
## 新增组首次超时后的原预算内恢复

旧282节点及role_smoke9节点完整通过；role_1首次cap20在target16.2142928s超时，capture charge18.2613637s、仅30个dot、无harness完成记录，不计任何该组通过节点。reader/pipes终态，cleanup=[]。失败原record与原admission/run.py均保留，Source epoch不变。

run_recovery.py沿用同一bounded drain，仅使用独立admission_revision_08.json路由；测试内六个wrapper单元节点仍按原admission.helper_pins核原run.py。revision_08静态cap10创建剩余四组：role_1_retry为原role_1完整节点，其余role_2..4原节点不变，各cap35，仍≤45；不继承部分dot。已费pytest154.7154115+后续140=294.7154115≤360；已费static43.4383354+revision10+finalizer12+saved22+terminal22=109.4383354≤120，组合≤480。所有尝试均计入总账。