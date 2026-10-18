# 单操作 historical numerical witness 有界对比

2026-10-17，DRAFT_NONAUTHORITATIVE。此为里程碑2的重复校验诊断，不是完整链验收或正式实验。

## 最新终态与当前决策

`entry_revision_06/common_slice_02` 已完成监控终态：600.656秒触发预设wall停止，child exit15，
没有访问违例，9个完整 Python 栈样本。准备67.897秒、第一个arm打开41.685秒；首个合成N0
Job为exit0/whole_job_quiescent=true，但外层登记和校验尚未完成，不能把这个Job算成N0通过。
没有进入arm1、CommonOwnerGenesis、Rref或本后继common。峰值采样RSS453,427,200 bytes，
三根最终工件21,242,690 bytes。`common_slice_outcome_02/postcheck.json` 核对794source/tested
pins、10锁及已观察PID+creation退出；不声称证明完整进程树为空。postchecker v2的Windows
强制byte-lock读取失败已保留；v3只改为用加锁前已读raw计算锁文件hash，工具exit0。

300/420秒采样指向 solver adapter identity 的7个Pyomo `.py` fresh-read fallback。保留所有原
identity函数、SHA256和stock version/distribution调用，只把这7个固定文件交给原CodeReadLease，
进行baseline/vendor7/vendor7/baseline四个新进程定向对照。均exit0，三目标identity与origins/
逐目标discovery计数相等；vendor两次各1253 hits，未列入文件的两次改变均fresh可见。

| 定向计时（每进程） | baseline均值(s) | vendor7均值(s) | 减少 |
|---|---:|---:|---:|
| adapter identity ×32 | 0.094716 | 0.061960 | 34.58% |
| parent identity ×8 | 0.027065 | 0.019381 | 28.39% |
| bootstrap identity ×1 | 0.373477 | 0.305787 | 18.12% |

仅每mode两个进程、bootstrap每进程一次；这是定向证据，不是稳定耗时分布或整链收益。
最终fresh readback见 `vendor_code_identity_postcheck_01.json`：208pins、11,827,296 bytes，
四个direct PID已退出；driver未证明完整descendant tree。没有native调用或资源准入。

新draft入口 `entry_revision_07` 保持149 repository code/614 test原清单，增加固定7项/128,055
bytes vendor清单；CodeReadLease原字节未变，root为D:/，cache仍仅exact156项。新active identity
绑定双manifest、路径与counts；vendor snapshots不进sys.path，module name/file/spec/loader逐一核对。
预载拒绝检查发现旧初始化间接导入Pyomo；修复为union lease开启后才导入，失败unit_checks_06
及其manifest保留。修后unit_checks_07为93pass/1权限skip、outer8.75秒，终态exit0。
最终包manifest为`ab0ad89e7efa04c57185dca779a822ea5ae70fc07c0fbb2cd92f2e03360f1925`（33成员）；
最后unit_checks_09仍93pass/1权限skip，outer8.969秒。审查补齐了紧邻lease开启前的preload检查、
arm/phase退出时必需origins，以及原MetadataParseLease先退出再patch.undo的顺序；此前unit07/08
终态仍保留，不把较早包的检查冒充当前字节。

`vendor_code_entry_plan_05.json`的保存真实common._arm对照已实际完成：

| 观测 | entry06 | entry07 |
|---|---:|---:|
| 数值校验arm_seconds(s) | 38.905162 | 36.279179 |
| 含装载/收尾outer(s) | 51.859 | 48.953 |
| 采样峰值RSS(bytes) | 239,742,976 | 240,025,600 |
| 最终工件(bytes) | 21,335,141 | 21,531,695 |
| fresh source/tested-copy项数 | 802 | 808 |

每配置一次，固定各120秒/512MiB/64MiB、串行，两inner/outer均exit0且无cap；arm减少6.75%，
outer减少5.60%。science和完整audit原始bytes相等，两metadata receipts原始bytes也相等；
149code/614tests、7vendor、461saved、33把锁及36old pins重核。vendor7逐项实际命中，receipt
与退出origin为同一7模块映射。`vendor_saved_arm_comparison_02.json`、postchecker v2及其实际
exit0工具终态保存，独立窄PRE_SEAL findings闭合。baseline/role/manifest/runner/limits替换会拒绝；
原postcheck v1和comparison01保留。下一诊断保留entry07。

当前包实际pytest parse_path接线另做一次13项sampler组件回归，13pass、outer27.859秒、
无cap；14份lease receipts均为exact156项和同一7模块origin。808 source/tested copies、
149code/614tests/7vendor、原36pins、解释器环境与已观察PID清理核对完成，见
`vendor_configured_sampler_checks_01.json`及独立postcheck实际exit0终态；未重复保存arm对照。

这一对测整个入口后继：code lease提前包住fixture导入和清理，metadata snapshot及退出顺序保持
原点。因此不把6.75%单独归因给7文件；隔离归因仅来自先前micro。运行时原chain07并行存在，
仅一对，不估计稳定分布、完整N0、common/Genesis/Rref/Actual或完整链耗时。尚未启动新长链。

## N0剩余热点及下一实现边界

对当前实际路由的只读静态展开（非600秒运行的实测计数）：phase_archive非空时，
BootstrapOwner._check恰7次bootstrap identity，每个root由micro确认含45次adapter identity、
90次stock version与90次distribution。owned成功transaction+run子路径含30次owner检查，
仅此已为210个bootstrap roots/9450个adapter leaves，尚未包括constructor/outer replay/parent。
这些调用跨既有观察窗口，不能以局部memo直接删除。

首个N0的_finish_N0_terminal含两次显式prepare，末尾_replay双registry又各build一次，即
4次旧prepare/16full+16fresh。pending_post_N的inspect又对每个retained slot增加8full+8fresh；
registry会重放每个已登记slot。资源_headroom还有36次目录绑定、三目录Job首个wait sample
另至少45次，后续sample各12次；它们承担前/中/后freshness，不作为无条件可删除重复。

当前complete_group会恢复保存的OWNED_CONTINUATION，覆盖numerical fixture中的坏锁wrapper，
因此实际slice没有按arm重复执行该坏锁注入，不把它算作此次慢点或可节省调用。

较大收益需要versioned verifier/bootstrap/owned/roster成功路径，新的操作内proof激活/失效、
receipt/identity、逐窗口失败矩阵及scientific audit/decision/projection/journal等价。现有group
operation witness绑定GroupWitnessSession/Handoff，诊断bridge退出会把Handoff置failed，
不能直接承接paired成功。完整hour0和所有后续出口继续OPEN，下一修改应解决这条接线。

## 当前 fresh slice 终态与修复

`entry_revision_05` 最终包（149 code/610 test，`common_slice_plan_03.json`）已实际执行一次。
进程在 258.859 秒以 `0xC0000005` 异常退出，监控未触发时间、RSS 或存储停止；采样峰值
352,792,576 bytes，最终三根工件 20,985,438 bytes。timing 只证明准备 83.470 秒、第一个 arm
打开 41.114 秒；第一个 N0 未完成。trace 与 outer 的计时原点不同，不相减估算 N0。
尚未到达 CommonOwnerGenesis、Rref 或本后继 common，不能报告本组收益或完整链时间。

`common_slice_crash_01/postcheck.json` 核对 788 项 source 与 tested copies 完全相等，失败根未变，
2 把锁可重获释放，已观察 PID+creation-time 集合为空；不声称证明完整进程树为空。
原 chain_07 的 36 pins 不变，原进程没有被停止、重启或修改。

第4次 C 定时栈 dump 在 `File ` 处截断；Windows WER 原故障 RVA `0x2fbfe7`。
一次每模式6秒的纯 Python frame-churn 差分中，C timer 以同一访问违例退出，RVA `0x2fc0a0`；
两者处于本机 traceback-dump 同一 unwind range `[0x2fbfc0,0x2fc4d5)`。
Python sampler 完成 68,806 次循环、101 次采样、64,016 bytes，exit0，两个 worker PID 均已退出。
这强力支持异步 C dump 竞态；缺少 native symbols/minidump，仍不宣称排除其他所有 native 原因。
证据与原 plan 的“2 direct workers / 0 worker descendants”字段澄清见
`stack_sampler_churn_pair_01/postcheck_and_erratum_02.json`，含 Event PID+creation-time 对应，原失败 bytes 保留。

新增 Python sampler 仅记录创建线程 filename/function/line，限制 frames、samples、bytes，不读源码
或 locals，不改变 trace/profile。worker 独占文件，停止信号后最多两次有界 join；IO、启动、预算、
body/采样双失败与 join 异常保持失败并记录清理状态。当前 `stack_observer_unit_02` 为13 passed、
outer exit0/0.938秒；短差分使用较早 helper bytes，两者的差别和 SHA 已明确绑定。
后继 slice 还须关闭该 target 的 pytest faulthandler 并验证插件缺席，完整 slice 稳定性待验。

此外先做了七代码文件稳定读取的成本上限测量（`stable_read_cost_01/cost_non_authoritative/`）：
原/影子/影子/原四窗、每窗128次。原合计0.750797秒，影子0.197622秒，减少73.68%。
影子在禁写删窗口内持专用 fd/bytes，每次仍2次 pathname stat、2次 fstat 和原 digest，逐文件
`(raw,stamp)`及全部 implementation pins 一致；没有替换原函数、module binding 或 `Path.open`。
它尚不含真实 wrapper admission 开销，只支持是否值得实现的判断，不能作为集成候选或全链提速比例。

随后 `stable_read_cost_02` 保留真正 fresh pathname open、两次 fresh-fd fstat、两次 pathname stat 和原
digest，仅影子 byte-read 复用：四窗原0.826029秒、影子0.377846秒，减少54.26%。原函数及代码未换，
文件 `(raw,stamp)` 与全部 pins 相等。两个影子都没有接入：前者会漏原 open 的 namespace 观察；
后者仍未证明原 byte-read 失败出口等价。它们不构成当前合同下的集成准入，不能用其比例预计全链。

修复已进入独立 `entry_revision_06`（manifest SHA
`6c0db76dd3bbcfb8281e69d7ad70cc18caaf7adef4d120c0aebb30bbcedef03d`，26成员、149 code/614 test）：
`unit_checks_05` 为77 pass/1权限skip，outer22.844秒；`sampler_smoke_02` 为13 pass，outer28.062秒，
实际关闭该 target 的 faulthandler plugin 并在 configure 核对插件缺席与 fatal handler off。
两次 source/test/member pins、interpreter 恢复、精确存储及已观察进程退出均通过；15项 monitor CLI
另行通过。`python_sampler_entry_checks_01.json` 绑定54项证据。先前 `sampler_smoke_01` 的
5 pass/1 fail/15 errors 来自测试全局 Path.open 故障注入影响 receipt hook，已将注入缩为 helper 的
输出构造器；原完整 snapshots、输出和终态保留，采样 helper 的实现未变。
新数值诊断计划为 `common_slice_plan_04.json`，一次600秒/采样RSS1GiB/新工件128MiB，
仅用于补修复后 N0/后续路径的进度与耗时证据；关键阶段可能仍达不到，未准入新的长链。

## 已闭合的单 arm 保存对照

同一个 chain_06 network-only N0，在两个新进程中分别运行一次原v1 oracle、两次diagnostic prepare。
每mode仅一次，固定300秒、512MiB sampled process-tree RSS、64MiB新工件上限。使用相同显式解释器
路径及code/metadata parse leases；oracle和每次prepare前分别重置parse window，stock distribution
discovery每次执行。未使用static identity shortcut；真实native调用为0（固定solver-forbidden路径）。

| 观测 | full-only | operation reuse |
|---|---:|---:|
| prepare1秒 | 28.540805 | 28.098218 |
| prepare2秒 | 28.685692 | 19.470876 |
| 两次prepare合计秒 | 57.226498 | 47.569094 |
| 实际full numerical inspections | 8 | 4 |
| 原始context evaluations | 32 | 32 |
| sampled peak RSS bytes | 221323264 | 220909568 |
| 新工件bytes | 10895803 | 10895753 |

第二次prepare减少32.1234%，两次合计减少
16.8758%。这是一个固定输入的单对结果，不是统计分布或完整链耗时估计。
第一次的四次full检查仍执行；第二次为八次数值证明复用，依旧进行十六次原始context观察。

两mode的783项source/package/test/evidence pins与461个保存文件一致，旧科学decision/audit exact一致。
模式、ordinal、实际full/within-prefix/cross-prepare/context次数、proof role、随机session、proof basis、
envelope与execution receipt hashes均闭合。各自33把保存锁可重获释放；已观察的owned PID+creation-time
进程树为空，RSS仅为采样观测。postcheck在两次terminal后重新核对完整source与saved inventory。

unit_06为68passed（26.12秒），monitor_unit_02为3passed。
monitor测试固定完整outer SHA后执行其未改动AST helper，并实际验证child/grandchild清退、creation-time
误认拒绝和锁重获；此测试本身不代表完整CLI或saved诊断通过。两个saved模式另有各自真实终态。
独立只读PRE_SEAL复核未见本诊断范围的剩余finding；不构成official verdict。

确切包：`diagnostic_source_manifest_v1.json`，SHA `5dec7d5766827cb56e3bc441c13d3205f10dd231f48fcab6ce508db298604378`。
主证据：`saved_pair_comparison_01.json`、两个mode的outer/inner `terminal.json`、`request.json`、
`operation_receipt.json`及每次prepare记录。所有早期草稿、失败/旧字节检查保留，不替代本次固定字节。
原chain_07的36项启动source pins不变；未对旧进程发出停止、重启或恢复命令。

## 下一出口

候选尚未接生产exact-source/common/Handoff。生产必须先绑定真实Handoff token、guard全集与三arm独立槽，
并等完整exact-source/common返回成功、source与第二registry/末次观察/结果构造完成后才激活证明，
覆盖callback/cleanup/return故障和close/reopen replay，随后取得真实handoff slice耗时。
当前复用后的第二次prepare仍需19.47秒，不能假定去掉数值重算就解决全部成本。

慢missing-one拒绝分支保留完整key集合，`None`在unresolved disposition合法，因此不采用any-None提前拒绝。
详见`optimization_decisions_01.json`。完整hour-0、192h、整体性能准入、资源准入、seal/official review与
正式运行各门仍OPEN，未启动新长链。

## 已落地的路径顺序调整

另一项保留stock discovery的配置优化，将D site-packages放在C support之前，后者仍提供Pygments/Colorama。
没有新增selected distribution/result cache，stock version/distribution callable每次仍执行；现有locked
version parsing和stdlib自身内部路径缓存保持。4000次warm lookup的单对观测为3.685260→2.924389秒，
此比例不能外推。随后同码实际raw-audit对照为Rref 9.686548→9.512673秒、Actual 6.665008→6.367484秒，
两lane合计减少2.8829%。两mode完整1883模块集合、origins/文件SHA、764 source、140 saved和8 METADATA
现时核验一致，科学projection、selector record和bridge identity一致；没有执行真实solver。

配置已并入独立固定入口`validation_path_optimization_01/entry_revision_04/`，代码成员沿用entry03原字节，
仅修改path policy末两root先后，另保存predecessor manifest并更新package/launcher绑定。
新package SHA为`d13a08fe6db35e9c5c70b8204e3fb4d0091e43a3ef483e3951a561eac0667e43`。
入口77pass/1权限skip和12项实际routing通过，terminal、145code/604test、interpreter恢复、生命周期
bookends和已启动entry进程退出已核验。routing suite没有实际durable path cache命中，不能据此扩张路径性能结论。
证据见`path_order_comparison_01.json`及`validation_path_optimization_01/configured_entry_04_checks_01.json`。
该入口尚未启用跨common数值复用；两种优化比例不相加，不由此估计全链时间或启动新长链。

下一接线边界及保守计数已固定在`guarded_common_slice_design_01.md`：第一common两轮全部full，
整个返回后才激活三个slot；两个common预期24full+72reuses/192contexts。22次consume common来自静态下界，
不能作为生产次数上限。真实guard准备/保存owner重开成本与该slice资源预算仍待核，不用单arm时间代替。

路径顺序的窄 PRE_SEAL findings 已闭合。`path_order_evidence_erratum_01.json` 将历史 fresh/no-cache
措辞限定为每次调用 stock callable、没有新增 selected-distribution/result cache；parsed-version 与
stdlib 自有缓存仍保留。`entry04_path_order_evidence_closure_01.json` 绑定 d13 package、launcher、
对照 request/terminal 和 postcheck 的实际 exit0，共 34 项 SHA。policy 的 baseline 是 predecessor
C-first，当前 D-first 实测见 `path_order_comparison_02.json`；02 补齐 checker SHA，测量值与 01 相同。
d13 固定字节及其 78 项入口检查、12 项 routing 没有重跑，闭合的是证据表述与绑定。
见 `validation_path_optimization_01/configured_entry_04_preseal_summary_01.json`，official verdict 仍为空。

## 三 arm common 后继的受限接线检查

四个 versioned draft 模块已实现 fixed sibling 路由、加载失败回滚、闭包资源记录、全部原始 arm
清理与创建线程的外层退出。`group_unit_06` 49 passed / 103.37 秒，`bridge_unit_08` 52 passed / 4.27 秒；
各 outer 为 104.563 秒和 5.391 秒。真实三模块 cold definition probe outer 为 3.281 秒，全部末次
guard 通过，但没有发行 lease/token 或执行历史数值。窄 PRE_SEAL findings B1–B10 闭合；这不是
实际 common slice 或 official verdict。准确终态与字节见 `group_successor_checks_02.json`、
`group_successor_postcheck_terminal_02.json` 和 `group_successor_preseal_summary_01.json`。

已登记 fresh synthetic root + live analytic Rref 的单次测量包，最终计划见 `common_slice_plan_03.json`。
`entry_revision_05` 绑定 149 code、610 test 文件，复用 entry04 的 lease、path、policy 和 plugin 原字节，
仅增加固定后继/夹具及单一诊断 target；入口 helper 77 pass/1 权限 skip。
单次诊断上限 600 秒、采样进程树 RSS 1 GiB、新工件 128 MiB，覆盖准备、3 N0、genesis、
Rref、两个完整 common 和清理。原源码 Parent/Handoff alias 明确登记为测试 seam。
该次实际失败终态及已经测到的准备耗时见本报告首节；两个 common 耗时仍未知，不能续延预算或
用局部比例外推整链。
