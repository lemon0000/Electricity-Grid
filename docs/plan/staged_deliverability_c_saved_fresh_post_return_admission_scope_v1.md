# 自然返回之后的B_S续接：准入草稿

2026-10-28，DRAFT_NONAUTHORITATIVE；NFC8独立有界诊断合同，受控size前仍为可修订draft。依据[1344 open真实自然返回](continuation_handoff_20261028_saved_fresh_import_return_v1.md)。宽goal仍为持续推进F，不把本合同或单次return视为完成。Root唯一writer，wire_root_review仅只读PRE_SEAL，无official verdict/receipt/production seal。

当前前驱NFC7 checkpoint SHA b56159068165115b54866169be5fb228cbaad6079081b79b85291443a8d58ce4，16文件1138658B；累计866.467895100049s、不接受37条。旧73文件5158740B及各自预算/失败保持冻结。本包余26.659556800004793s留原包，不转用；关闭的PID40080不恢复。

## 真实剩余路径

冻结census2048 helper的diagnostic_import_once已经实际得到importer返回，但立即抛AuditCensusStop；pre-import runtime.source_bookend已执行，child source_bookends=2。load_bootstrap_adapter余下路径在本轮未执行：authenticate_machinery → NumPy fallback状态核验 → 13个源码函数与2类shape → freeze_adapter_roots → post-import/final Source49 bookend → sys.modules retained tuple → boundary.close → runtime.finish_import。随后才可能建立本地OBSERVED，再在另一次具独立profile匹配的路径中评估LIVE；两者均不打开role/P1/permit/F/science/resource/formal authority。

下一后继应保留2048前超限stop与所有原失败路径，在自然返回分支允许已验证result交还loader，并单独记录返回后的阶段。import census与后续成本分开，不把停止计数后的未观测open补成旧census事实。原helper/parent/core及NF7 records不动，需独立版本、输入闭包、constructor/oracle与PRE_SEAL。

## 首先完成的审查

1. 按当前source枚举完整调用DAG，计算runtime.entry、boundary._entry、check_adapter_roots、source_bookend及namespace graph重读倍数；不得让历史checker或post-import回调重复隐藏增长。
2. 检查authenticate_machinery在audit callback之外的code/default/closure读取；覆盖getter重入、metadata同对象改写、pending→authenticated顺序、重复认证/错误stage与保留primary/secondary。NF7的observed2/auth0不替代这些证据。
3. freeze_adapter_roots核adapter模块的13函数/2类，并调用held freeze_namespace_graph；当前reader的depth≤256、nodes<50000只是防护帽，不是当前图规模或运行成本。需要实际节点/bytes/retained对象及后续图bookend成本，不能从入口34个graph frame或import3.8277s反推。
4. 分清图image bytes、强持objects、sys.modules retained tuple、Python/native内存、process working set与private commit。NF7的138.8203MiB sampled child peak不证明128MiB retention达标或违规；已有256MiB/process与512MiB/pair sampled stop策略可作后继诊断候选，连续覆盖/descendants/正式资源门槛仍OPEN。
5. 固定新success/failure输出schema、profile/raw/packed/root上界及保存重开；不得要求仍以“未完成policy”的旧异常链作为成功分支。记录close前真实runtime phase与close后终态，明确OBSERVED与LIVE的独立profile前提。

## 有界诊断DAG及不变性

按agent.md第9节，本包仅生成返回后关键成本的代表性证据，不准入目标F。静态只读审查未发现getter必然重入：authenticate要求非busy，audit忙路径使用identity-only reader。当前确定断点为旧helper自然返回后主动stop；后继保留2048前的stop和原import错误，只有自然返回分支交还原result identity。原Source49、原图reader、全部freshness扫描与科学阈值保持；不采用跨调用cache，因为getter/回调之间的metadata/ABA freshness尚无可替代证明。

名义成功路径：raw重开确认旧loader_ready前15次namespace图，旧终态17另含stop后2次清理图；返回后authenticate1、finder_check10×14函数metadata行、namespace图6（含namespace close）、adapter图1初冻+8重扫，合计30图=21 namespace+9 adapter。返回后4×49=196高层source reads、boundary.close另EXE+4external reads、profile2及finally cleanup。post-import前两次Source49读取发生于active hook（98次）；source_bookends最终预期5。旧NFC7报告的2实际为pre-import 1+失败后cleanup 1，旧交接中“两个均为pre-import”的描述在此更正，原记录与bytes保持。真实getter数量和图节点/bytes未知，本诊断测出，不把静态倍数当耗时。失败可提前结束或增加清理扫描；总图调用40帽、50,000节点/depth256原帽保持，canonical graph image另加4MiB诊断帽；返回后getter另限每类1,000,000事件，超限保留失败，不重启/扩大帽。

新namespace/helper/probe33/core35/parent32及validation、constructor、checkpoint独立版本。仅增加diagnostic计数/计时和tagged graph；图序号、kind、enter/exit及实际nodes/strong objects/canonical image bytes逐次保存。image序列化计入图耗时，nodes/objects只描述reader图，不等于retained heap/RSS；code digest和外部opaque身份范围保持原义。getter计数只指自然返回后active hook可见事件，busy/idle分别保存，不能宣称全部finder行为闭合。计时buckets有嵌套，不求和成整链耗时。

执行DAG：size → register → 唯一20-node unittest（原14项，其中6项native audit反例定向新helper，新增6项）→ 独立PRE_SEAL → 唯一startup → profile admission → 唯一import_discovery → saved reopen → checkpoint。startup失败则不启动actual；actual失败/超限则保存raw/receipt并仅做失败元数据checkpoint。当前没有独立import profile，成功只能为OBSERVED，另需boundary CLOSED、Source49最终bookend和finally runtime/resource CLOSED；CLOSED boundary及stage2单独均不足。原核验与失败图层不跳过，不把已停census之外的open补入1344事实。

## 固定预算、资源与保存

本包独立预算81s = static65 + unittest16；沿用旧累计866.467895100049s与不接受37条，不退款/重置/转移旧余量。

|阶段|cap秒|依据与次数|
|---|---:|---|
|size|6|原1.74s，增加2 helper及输出闭包；一次|
|register|4|原1.47s，增加namespace/validator快照；一次|
|unittest|16|原8.95s，新增6 fault nodes；一个child|
|PRE_SEAL|5|原3.13s，完整fresh inputs和已执行unit复核；一次|
|startup|6|原3.85s，独立新transport/profile；一个child|
|profile admission|5|原2.96s，startup profile/pins重开；一次|
|post-return actual|30|原9.36s外层包含3.83s import；未知14次图、140 metadata行与196 reads留约20s有界测量窗口；一个child|
|saved|5|原2.97s，增加profile/metrics/图重开；一次|
|checkpoint|4|原1.90s，完整root/pins/预算重开；一次|

以上是诊断stop caps，不是已证明的整链性能准入。无并发child、无重试、无自动顺延。沿用原memory_drain_v1固定bytes/SHA：80B PROCESS_MEMORY_COUNTERS_EX，parent pseudo HANDLE与原child HANDLE/PID绑定，每进程256MiB、两者512MiB sampled peak WS/private停止，0.01s请求轮询、最多4096样本、last_live_poll_only、O(1)计量。query/handle/PID/clock/over-limit/sample-limit/timeout/输出超限任一失败即拒绝并收尾，保留raw与primary/secondary；不在exit后补采。startup需自己的native healthy样本，不能复用旧PID采样。

Windows API含义与既有采样限制沿用[冻结NFC7合同](staged_deliverability_c_saved_fresh_census2048_admission_scope_v1.md)。continuous_bound_verified、combined_retention_verified、resource_admission继续false；不声称连续/descendants或128MiB retained-root准入。source/input fresh读取逐阶段前后保留；原v3 leaf仍唯一历史checker，不递归重跑所有controller。新root至多17文件/4MiB；新增import_profile.json≤1MiB，registration≤786432B、unit exit≤32768B、两receipt各≤1MiB、saved≤65536B，stdout≤131072B、stderr≤32768B。20个census帧、至多40图对及22 stage的最坏canonical bytes由size独立计算绑定；超出则拒绝。命令仍≤30000 UTF16，profile decode≤1MiB并要求eof/无尾巴，失败也不放宽。

32KiB stderr总帽同时充当心跳/无进展诊断约束，主线程deadline和采样循环提供硬停止。无进展不追加预算：保留最后stage/graph/census及raw，未知子端状态保持未知；父端kill/wait、pipes/readers/writer/stdin/HANDLE需各自终态。scope、source与实际命令/环境/input闭包由size/register精确绑定；首次受控size开始后本包已执行bytes冻结。普通源码生成/只读工程检查与PRE_SEAL人工审查wall不计作capture秒，账中逐项保存受控phase真实charge。

所有科学模型、阈值、原Source49、B1–B3/P2与发布绑定字节保持。当前没有新P1/实际role/OwnedChild/Job/F、model/solver、native校准、长实验、外部下载或paid query；production/official/native行为认证/科学/资源/正式/run authority继续false。后续工作仍须唯一writer、独立只读PRE_SEAL及适用的实验准入。

core35.finish_import??????????entry?????observed immutable raw??versioned????probe33??????profile raw?????????????before/after_finish_import????finish????????runtime.entry??????????
