# N0 historical replay bottleneck

## 2026-10-18 旧chain07主体终态：通过，独立后验待补

旧配置主体已完成：exit0、1 passed、wall259910.325371s（72小时11分50秒）。三arm N0/common、
Rref/Actual、paired commit/readback、全部关闭后重开重放均有主体终态证据。3个原进程已退出，
36项启动前后源码、当前源码及tested copies一致。observer在72小时先到期，未运行独立postcheck/report，
不是链失败；没有重跑链或启动新的长验证。42项逐阶段记录及只读核验见
`chain07_terminal_status_20261018_01.json`。独立保存复验/清理门及完整报告待补，M2未宣告完成。
旧版72小时不是优化后继ETA，也不是正式实验耗时；后续draft优化证据沿用下文当前后继段落。

## 2026-10-18 当前后继：单窗 source 与 post-negative 复验

本节优先于下文按时间保存的旧状态。当前为 `DRAFT_NONAUTHORITATIVE`；M2、整体性能审查、
资源准入、seal、official review、native/formal execution 和正式结果均未通过。
本轮只修改独立 draft 和测试接线，未改变 `chain_07` 的进程、配置或绑定源码。

第一处新瓶颈已经接线：三个 missing-Actual 分支之后，每轮原来分别公开复验 Rref 和三个 Actual。
每个 Actual 又两次递归复验 Rref，故每轮是10个 retained 主体、160次原 source prepare；三轮为480次。
`h1_selector_post_negative_validation_development_v1.py` 将每轮收拢为一个同步窗口，原 source 只在
窗口首尾各执行一次，160个内部位置借用同一完整值；三轮共6次 prepare、480次 borrowed return。
减少474次（该子组98.75%），这是调用量减少，**不是整链墙钟提速实测**。

每轮仍执行 Rref7次、各Actual1次 retained 主体，保留原 preparation/bind/inspection、
process/environment/archive 与 Actual→原Rref 依赖检查。先按 lane 排序非阻塞获取三个 Actual guard，
再获取 Rref guard；全部获取后才设置引用标记。私有 registry lock 原子登记操作，foreign caller
不能覆盖或清除原操作；同线程 caught reentry 会 poison 原操作。所有退出尝试逆序清理，首错保留，
仅在全部已获取 guards/marks 与 registry 清除后返回 plain JSON，未签发 ParentCompletion 或执行权限。

这是新的校验观察身份：四个公开调用合成一个四Parent同时持锁的窗口。每个内部 source 的 I/O、
原失败顺序、原公开 guard 调度不等价；不声称覆盖 top-level 调用间或首尾之间的瞬态 ABA，
不声称完整动态依赖闭包。窗口只清除缓存入口；旧消费者派生输出仍按原生命周期存活。
不跨 Parent.run、run_job、before_release、on_quiescent、capture_actual 或 common 回调复用。

| 当前证据 | 终态 | 覆盖范围 |
|---|---|---|
| `post_negative_validation_unit_06` | 136 passed/22.90s；outer24.312s/exit0 | 新窗口、原公开方法体160→2对照、并发/失败/清理、真实helper loader和三轮接线 AST；Parent transport/source arithmetic为显式fake |
| `post_negative_v4_collection_01` | 1 test collected/4.32s；outer5.531s/exit0 | 当前完整v4文件只完成collection，没有执行完整test |
| `post_negative_source_window_monitor_02` | outer58.781s/exit0；inner56.969607s/exit0 | 真实原source及其guard，单窗44.465935s、2prepare/160borrowed/10retained；Parent transport显式fake，0Job/0native/0真Parent |
| `post_negative_source_window_postcheck_02_non_authoritative` | exit0 | 原134文件、10个canonical锁逐一获取/释放、907源码/135保存输入/旧36pins及owned PID退出 |

真实source验证方式是 entry/tail 的完整 canonical typed projection SHA256 与独立保存的
`source_complete_fields.json` SHA256相等（`2cf03606174d4cfba771917c3eff9557e54b472f047d88130993ba17d915eb5c`），
其中包含 decision/audit bytes；未重新跑160次原source作墙钟基线。外层采样RSS峰值206163968 bytes，
新增工件13570063 bytes，低于预先固定的180s/768MiB/128MiB上限；child38476已退出。
探针登记的私有句柄/patch恢复分别由inner terminal、`bounded_closed_receipt.json`、
`path_closed_receipt.json`及`window_receipt.json`支持。
最终plan02 SHA为`456aab2a3b6324cb5386fd57bbd0cdf0066f9462bdb6e7159834a9add29b0601`。
未运行的旧plan01及其预启动脚本保存在`post_negative_validation_baseline_01_non_authoritative/unlaunched_probe_draft_01`；
该baseline目录只保存文件前像，不是实验性能基线。unit02/03/04的exit1保留：显式fake原方法体
oracle依次暴露closure、canonical wrapper及未替换fake source的问题，修复fixture后unit05/06才得到完整绿色终态。
只读PRE_SEAL审查未发现本轮draft剩余实现级正确性缺陷，记录在
`post_negative_validation_preseal_findings_01.json`，不是official verdict/review receipt。
`post_negative_validation_closeout_01.json`再次核对当前tested bytes、全部终态与旧36pins；
8个相关Python文件AST及whitespace、`git diff --check`通过，未为收尾重新启动任何测量。
实际pytest/诊断命令和限额保存在各attempt的`request.json`及最终plan02中。

成功Handoff已使用 `h1_selector_parent_validation_operation_development_v2.py`：13 bundle、8 pair、4 records
共25个窗口，2408次是logical source请求，原source prepare为50次；完整成功状态机已由既有unit03/05
及本轮相关回归覆盖，早先单个真实source窗口为41.012528s（fake Parent transport）。下文的
256 full/38528 context及2408 physical prepares属于早期v1后继，不是当前v2执行量。

尚未消除的已计数部分是四个Parent构造/run/oracle：Rref94次、每Actual206次，共712次原source。
加上成功Handoff50与本轮post-negative6，相关子路径静态小计由至少1242降到768；不含Bootstrap、
common、capture_actual及其余paired/reopen/report成本。详见`post_negative_validation_route_counts_01.json`。
下一步先拆分这712次中不跨Job/外部回调的安全窗口，并补最小genuine Parent/Handoff证据；之后才重建
完整v4 configured entry的allowlist/test closure和整体预算。`entry_revision_07`仍未接纳这些新后继，
旧configured runner不能通过替换pytest目标直接启动完整v4。reader v3仍维持STOP_BRANCH_RETAIN_V2。

旧chain07最新nonblocking采样位于consume440→第二次readback367→correspondence222/common检查，
相较此前同一readback中的Parent复验已有内部推进；累计约71.44h仍无terminal，不能给出剩余ETA。
该观察保存在`post_negative_old_chain_observation_01_non_authoritative`，未改动旧进程或active数据根。

## 2026-10-18 最新终态与采用决定

本段更新下文早期 attempt 的状态；旧失败记录原样保留。M2、整体性能审查、资源准入、
封存、official review、正式运行及正式结果仍未通过。完整 v4 target 仅做了 collection。

| 检查 | 实测终态 | 证据范围 |
|---|---|---|
| `parent_common_regression_unit_02` | 93 passed，47.02s；outer48.313s/exit0 | 当前 creator-thread 修复、私有路由、proof/cleanup 状态机；fake transport/arithmetic |
| `parent_source_scientific_oracle_monitor_03` | outer470.781s/exit0 | 保存 source 的全部 typed fields、decision/audit bytes 相等；显式 fake host/activation，非 genuine Parent |
| `parent_source_profile_monitor_03` | source39.006289s，含 profiler；outer50.922s/exit0 | 严格导入路径及模块 origins；只覆盖 repo path lease，不能外推新完整 root |
| `fresh_owned_source_cost_monitor_03` | outer352.297s/exit0 | 新建真实 owner、一个合成 Windows N0 Job、登记及关闭，再做一次原 source；不创建 common/Parent/Rref/Actual |
| `bounded_entry_v3_monitor_unit_07` | 131 passed；outer3.640s/exit0 | v3 原 IO 故障、next-dispatch 漂移、orphan/close poison、monitor observation 异常 |
| `fresh_source_reader_pair_postcheck_01_non_authoritative` | exit0，**STOP_BRANCH_RETAIN_V2** | 同输入单对 source wall22.423639→23.217933s，未达到5%采用限；不接入v3 |

真实新 N0 诊断分解：owner open15.227563s、N0 complete295.572059s、owner close0.000158s、
原 source17.801640s。其余为测试 setup/teardown、入口及监控；不能把这四项相加叫完整 hour0。
三个已观察 owned process 均退出，10把锁可重获释放，889 source/tested copies 与旧36pins一致；
171 code paths 写方式重开无写，hooks/handles 清理完成。基准目录为
`D:/h1_fresh_owned_source_cost_03_non_authoritative`，仅用于本任务已完成合成输入。

reader v3 试图减少自身 full guard 扫描，保留原科学 stat/open/fstat/actual-read/close/stat 观察；
明确改变自身额外 guard 的检查时序。它通过故障检查但未显示实测收益：source wall慢3.54%，
outer35.218→35.719s。按预登记出口停止，不再调参或反复跑同一局部对照。
两版各12,086次真实 stable reads、49,156,606请求字节，完整 source fields 与 audit 相等；
134个输入文件和10把锁在 candidate 前后分别补检。锁 canonical bytes 的依据是原 creator 合同，
没有追溯声称 baseline 运行中的 transient ABA 已被观察。复合 postcheck 保存全部 hashes。
pair01未运行；baseline02/03在 source prepare 前因 fixture 前置条件失败，candidate02/03未运行，均保留。

原 saved oracle03 的 import-window 证据不足由 profile03 和 fresh-owned/reader04 后继严格补齐，
不能回写为旧 attempt 自身已观察。原源码/结果/依赖数据不缓存；代码身份 bookends 仍仅是
full-target 的 test-only fixture 范围，既不是生产身份成本，也不证明 transient code/package ABA。
单 original source 仍需约18–23s；2408次 Parent source prepares/38528 contexts 是尚未完整实测的
条件调用量，当前不能据局部读入口减少扫描就启动长链或给出全链 ETA。
下一出口是减少该嵌套验证路径的实质成本并完成 genuine Parent/Handoff、paired commit 与 reopen。

## 2026-10-18 Parent 数值复用接线与出口

新的 `h1_selector_parent_validation_operation_development_v1.py` 与
`h1_parent_source_n0_witness_development_v1.py` 已接入 Handoff4 draft。
通过私有 functional successors 连接 Parent/source/preparation/bind/worker/snapshot/inspection，
原模块及其 callable 不改写；原 source/registry/transport/context 观察保持。
每个 Parent 的首次完整 validation 内16次source均full，完整尾检成功才激活其独立proof。
后续只复用历史数值恢复；失败无旧路径fallback，解锁前清proof，全部外层清理后唯一commit。

静态及fake functional route 的成功计数（包括records自身重建）为：
13 bundle validations、150 Parent validations、4 standalone rebuilds、2408 source prepares，
256full/19008复用/38528原context。它们不是墙钟收益或真实Parent成功证据。
PRE_SEAL发现的direct dispatch、Handoff私有入口、abort后commit及重复abort覆盖首错已修复。
`parent_common_regression_unit_01` 为89 passed/32.61s，outer33.907s/exit0，source稳定；
覆盖真实Parent方法code配fake transport/arithmetic、真实finally AST、proof状态机及common bridge。

`parent_source_scientific_oracle_monitor_01` 已按投影预算停止：旧source一次35.564281s，
新source首次full一次34.017138s，decision bytes与source audit bytes相同。不能扩称所有source字段相同。
首candidate后估计剩余16次会越过预登记540s，因此正常抛错、未激活，outer86.094s/exit1，
不是17次oracle通过。183保存非锁文件、source、old36稳定，owned PID已退出；无Job/native。
该次未使用full-target adapter+Bootstrap2的test-only纯代码identity bookends，不外推完整链耗时。
后继诊断必须匹配该fixture scope并比较全部source字段；不缓存source/dependency data。

Bootstrap4尚未接入当前全链：需要roster successor、tuple common transport和genesis successor，
并区分active v3 execution与v1 source compatibility，不能简单替换owner或模块别名。
当前先闭合Bootstrap2既有链，避免在M2前引入新的不兼容transport；这不构成Bootstrap4已被整链验收。
M2、完整路径性能准入和全部正式门禁仍OPEN；下一必要出口是代表性实际Parent/Handoff与paired/reopen。

## 2026-10-18 当前优先瓶颈：Parent source 的乘法展开

M2 仍 OPEN。成功 Handoff 的条件调用图已由独立只读分析复核，并由
`postcheck_parent_bottleneck_v1.py` 对关键调用位置和成功计数断言核验：
150 个 `Parent._retained` 主体分别展开成8次snapshot rebuild、16次source prepare、
64次full N0 hour audit。合计 **2,400次source prepare、9,600次full N0 audit、
4,800次registry prepare、9,600次registry load和约19,200次source-window load**。
这还不含4次records自身的rebuild/sequence inspect、common、producer和reopen。
这些是静态条件计数，不能换算成已测墙钟占比或全链ETA。

乘法来自 `Parent._source` 的一次prepare加bind内两次prepare；各prepare又有两次
request/rebuild，snapshot再执行两次build。inspection前后还各有一次rebuild。
因此只缓存 `inspection.sequence.inspect` 或hour arithmetic，不能移除source重建主体。
优先实施边界已收敛到versioned source reconstruction与完整有序依赖closure；
不再继续纯摘要缓存，不重跑未改变的完整长链。

`parent_inspection_footprint_monitor_03` 以120.391s wall cap停止，未完成一次conditional
inspection；没有完整footprint，不能当作收益证据。改为可保存停止前证据的plan04：
一次20秒业务前缀、75秒outer上限，实际prefix20.007879s、outer33.016s，按计划抛出
受控异常并正常清理，原检查exit1。348个GIL样本中277个经过inspection source、261个经过
phase fresh、96个经过完整hour inspect；共记录11,626个open events/317个paths。
GIL样本不能当作墙钟占比。165个code路径写方式重开无写、183个保存非锁文件、source pins、
old36和已观察进程清理核验闭合；没有新Job/native或live Parent credential。
该保存检查恢复了 source fixture，未运行full target的 `identity_bookends` test-only cache；
因此metadata/code-identity成本尤其不能外推成当前完整v4 target的耗时。
plan04外层第一次误用 `-I` 因psutil不可见在import阶段退出，未建输出/启动child；
实际outer沿用原 `-B`，业务child仍固定 `-I -B`。

锁观察更正：旧monitor的 `externally_owned_input_locks_not_touched=true` 不能解释为
内部verifier从未打开input locks。plan04实际观察worker execution.lock的7次只读open，
原reader还保留lock identity bookends；没有获得writer byte-range lock。
不声称access time无变化。原plan/terminal字节均保留，更正和证据hashes另存
`parent_bottleneck_postcheck_01_non_authoritative/terminal.json`，该reconciliation exit0
不改变两次原检查的失败/停止终态。

独立PRE_SEAL设计审查明确：现有proof不能直接缓存整个Parent._source/_inspect。
registry authority/config/packages/manifests/archive/catalog/GAPS、current-source的RTS CSV namespace、
完整transport/archive/lock、process/env/clock与Actual→Rref依赖都须证明覆盖。
Bootstrap的970个phase pins不在此调用路径，不能直接拿来替代。更窄的historical prefix
复用仍需canonical primitives、完整fresh bookends、新active execution receipt，以及所属完整
Parent site成功后才能激活；不能复用已关闭 `_HourScope` 的nonce对象。
该窄数值后继现已实现draft接线，状态与未关闭出口见本文首段；整个Parent缓存仍未证明或采用。

成功common复用五模块draft已完成接线：22个common位置及2,112个原context保留，
算法目标/状态机为24full、24within-prefix、1,008cross-common reuse。
53项bridge/cleanup、10项保存报告纯逆投影、13项grouped状态机以及真实五模块cold definition
已分别终态通过；范围和fake seams见 `rq2_h1_handoff_common_operation_development_v4.md`。
v4全链target只做了collection，没有完整执行；不是实测528→24或M2通过。
真实anchor、bridge pending receipt、外层清理、成功commit的联合出口仍未闭合。

## 2026-10-18 当前结论：修复失败路径，停止无整段收益的分支

M2 继续 OPEN。Handoff v3 的 missing-all 独立 target 已通过：先完成 Rref，再检查缺失，
不创建 Actual。Rref 为 82.384148s，拒绝为 **8.095914s**，拒绝期间 common 重放 0；
outer 为 **110.812s / exit0**。883 source/tested snapshots、167 代码写方式重开无写、
4 锁、2 个进程（含外部采样器）、hooks/handles 和旧 36 pins 已核验。
证据为 `negative_handoff_alias_monitor_03/terminal.json`。
这只关闭该失败 target；三条 missing-one、三 Actual 成功、paired/reopen 仍待完整验证。
5 项 one-shot/no-None 失败检查另已通过，outer32.703s；观察异常不能吞掉后重试。

此前 ordinary unit_01 在 240.140s cap，未完成首 Rref；configured alias01 在 240.375s cap，
已完成 Rref、首 Actual 未完成，尚未进入失败矩阵。两者均非通过，现场保留。
alias01 的 882 sources、旧 36 pins、所见 PID 和 5 锁清理有终态。
新的负向观察位置及 compound-fault 首错差异见
`docs/model_spec/rq2_h1_negative_actual_precheck_development_v1.md`；成功路径保持原 22 个 common 位置。

原 GIL 线程采样中 159/228 个样本位于两个 JSON 的 open；直接 72 次 fresh-read 小比较合计
仅0.004773s，不能据线程采样认定 I/O 占七成。外部 py-spy 使用 `--gil --nonblocking`，
只读目标、不安装 Python profile/trace、不暂停；alias03 前90秒2666 samples/835 errors，
只支持该 prefix 的采样分布。未运行、未接入的输入快照草稿保存于
`immutable_input_proposal_01_pre_review/`。

纯 repair 摘要缓存保留每次 JSON read/pin/parse 和93行 rational 构造。
局部 ABAB 4×128 调用为0.243261→0.215411s（11.45%），26项隔离 unit 通过。
实际同 target 却为 alias04 **111.218s**，收窄非命中 guard 后 alias05 **110.547s**；
相对110.812s仅约 **0.239%**，未达到 plan05 预登记的5%整段采用门槛。
决定 **not_adopted_stop_this_branch**，不接入后续完整链，也不继续微调。
`negative_handoff_performance_postcheck_01_non_authoritative/terminal.json` 为 exit0：
各实际 tested-byte 快照、latest889 sources、168代码写方式重开无写、旧36 pins与清理已核验；
科学投影及3个 selector_record 逐字节一致，根相关 binding/commit 分别按自身 SHA 验证。
固定顺序、旧 chain 并发且无独立重复统计，不外推整链提速。

真实 owner 六节点 path 接线已 exit0/56.578s，inner54.928s；owner_open33.9098s，
旧33.8549s，未显示主要收益。872 sources/tested copies、165代码写方式重开无写、2锁与 PID 闭合，
无 Job/native。实际 saved common path 接线收益仍为下文29.546419s及其有限对照范围。

下一个瓶颈是 Parent._validate/_retained/_inspect、Actual→Rref 嵌套重放，以及成功 Handoff 的
22次 common（静态528次 full numerical hour audit）。生产接线必须保持全部 freshness 位置、
原 common 完整 report 兼容字节及回调/失败窗口，才能检验操作内数值证明复用。
本条记录时diagnostic session不能发行consume成功凭据；其后五模块draft接线进度见本文首段，
24次full尚未通过真实完整Handoff或取得完整耗时实测。
不启动新长链。M2、整体性能启动审查、M3–M6、resource admission、seal、official review 和正式运行
继续 OPEN；未使用 native 校准或正式运行授权。

M2 完整链继续 OPEN，正式实验没有启动。本目录全部为 development/non-authoritative 证据。

## 已测收益

同一 saved network-only controller/pins，先测旧 verifier 四次 prepare，再测四次经过完整 build 确认的 proof prepare：

| 范围 | 旧路径 | 四 build 后继 |
|---|---:|---:|
| 四次合计 wall seconds | 108.8038 | 84.8146 |
| full numerical replays | 16 | 4 |
| fresh revalidations | 16 | 28 |
| context evaluations | 64 | 64 |

节省 **22.05%**。这是一次固定顺序对照，包含 warm-up/缓存顺序因素，不是独立重复统计或整链加速比。每次 decision/audit raw bytes 与旧 verifier 相同，full fallback 也通过等价校验。

outer exit 0、235.594 秒，采样峰值约 213.4 MiB。postcheck 核对 811 个 source snapshots、461 个 saved files、33 把锁和旧 active chain 的 36 pins。精确数值 verifier SHA 为 `407e8056d08f3c60a955f540a9bc7155319549a4a40834501657fd54f908f6ea`。

测量后 bootstrap v3 仅强化 receipt publication 异常处理，该 bootstrap 不在 saved 数值路径内；新字节另有 `unit_07` 的 134 passed。该对照不能称为当前完整 bootstrap 通过。

证据：`saved_four_plan_01.json`、`saved_four_monitor_01/terminal.json`、`saved_four_01_non_authoritative/`、`saved_four_comparison_01.json`。

## 更大的重复量与主要修复

当前 slot 四 build 以外，每个旧 slot 在后续 bootstrap 内静态至少 full prepare 26 次；三个 arm 依次启动时为 `26 × (0+1+2) = 78` 次。生产 common v2 每次有 4 个 roster replay 窗口、每个 replay 两次 registry view，三 root 合计 24 次 nested N0 build；诊断 common v3 多一个 replay，合计 30 次。成功 Handoff 的静态路径为 22 个 common calls，即 132 次 direct source prepare 和 528 次 nested registry build。这些是当前调用图计数，不是完整执行实测。

新 verifier v3/bootstrap v4/owned v4 在同一次 bootstrap lock/nonce 内，为每个 root/pins 保存独立证明。首次完整 build 返回后才激活，后续每次仍有 16 个 context observations，使用 `0 full +8 fresh`。最多 3 roots、64 prepares/root；scope 外路径仍 full，旧运行字节保持不变。

`registry_unit_04`：精确三源 115 passed/40.79 秒，包含三个 root 各 26 轮、96 个 context failure edges、每 root poison/close 故障和无 capability 拒绝。合成协议中的 78 prepare 共 12 full numerical replays；这不代表真实 registry 耗时。

私有 capability、真实 owner/thread check、getter fail-closed、首个 build 确认和 all-root cleanup 的 scoped PRE_SEAL findings 已闭合。`registry_sources_02_non_authoritative/patch_manifest.json` 与 `registry_rebuild_check_02_non_authoritative/terminal.json` 确认从固定 predecessor bytes 重建当前三源。此为 PRE_SEAL 证据。

## 冷加载真实 N0 诊断

`fresh_n0_monitor_01`：exit 1/126.688 秒，在 Job/attempt 写入前拒绝旧 symbolic profile。新配置绑定新 bootstrap implementation，继承夹具却提供旧 profile。0 journal rows、0 Jobs；820 源和旧 36 pins 不变，观测进程退出，两锁重获/释放。失败现场保留。

夹具修复为真实 symbolic reader、定义前固定 resolver callable、独立 successor profile 和 hash readback。`profile_unit_01`：1 passed/57.43 秒，profile 只改变 `implementation_sha256`，科学字段及旧 bytes 不变。

`fresh_n0_monitor_02/terminal.json`：600.437 秒按 wall 上限停止，child exit15，未完成 N0 登记。一个真实合成 Windows Job exit0、whole_job_quiescent，耗时 61.766 秒；这不是整个 N0 通过。826 源和旧 36 pins 未变，3 个观测进程已不存在，10 把锁重新取得并释放，原现场保留。没有延长预算或原样重试。

## 命中真实读取瓶颈的优化

实际栈反复位于 registry dependency 读取及 identity 的源码读取。原 `raw_ingress_v1.read_stable` 对每个文件请求 `cap+1` 缓冲；registry 的 cap 为 32 MiB，而约 983 个 dependency 多数只有数 KiB。新的 configured entry 只对原 canonical 函数的 exact code/globals/caller 作代理，将请求长度改为刚观察的 `before[2]+1`。原函数、每个 stat/open/fstat、全部文件内容和末次 pathname identity 检查继续执行，不跨调用缓存输入或结果。请求缓冲字节数不是实际磁盘 I/O 字节数。

`bounded_stable_read_entry_v1.py` 内部创建并持有真实 CodeReadLease，将 raw-reader、entry 和 CodeReadLease 自身源码一并锁定；定义时 closure 保留 creator、dispatch 和清理 callable。它是新的 Windows/CPython entry contract，增加 caller-frame audit event，不声称 audit-hook 透明性。模型、阈值、旧科学模块和已有运行字节不变。

`bounded_entry_unit_09`：60 passed，覆盖真实文件 tuple 对照、边界增长/缩小/替换/短读/fstat 与 I/O 异常、线程及模块重绑、重复路径、setup/body 双故障和异常 repr/note 故障。首次异常保留，退出后 hooks、owner、handles、streams/proxies 有机器可读检查。原三个 N0 successor 的 115 项检查可以按 unchanged source hashes 复用。

### 实际 configured entry 对照

`bounded_registry_plan_02.json` 固定一次、两个 split、每配置各两次完整旧 registry build；120 秒、768 MiB、128 MiB 上限。这里没有 Job 或 native 调用。

| 完整 registry build | 原 configured entry / s | bounded entry / s | 原始声明 |
|---|---:|---:|---|
| training | 13.13835 | 1.16290 | exact bytes equal |
| holdout | 14.12769 | 1.40080 | exact bytes equal |
| 合计 | 27.26604 | 2.56370 | 减少 90.60% |

outer exit0/38.656 秒；836 源和旧 36 pins 未漂移，全部 7 个 vendor origins 实际核对。closed receipt 确认两个 hooks 恢复、owner closed、handles/streams/proxies 为零；164 个代码路径可再以 r+b 打开且不写入。执行数据见 `bounded_registry_entry_02_non_authoritative/terminal.json`、两个 receipts 和 `bounded_registry_monitor_02/terminal.json`。这是一次固定顺序对照，不是统计重复或全链提速率。

前置 `bounded_read_probe_01_non_authoritative` 的 4 KiB/256 次微对照为 0.99112→0.05437 秒；独立 registry typed v2 对照为 11.57881→0.82891、12.72499→0.78230 秒。typed v2 未接入 bootstrap；主路径采用上述 entry，以保留既有科学模块和所有观察窗口。

`fresh_n0_plan_03.json` 固定 845 源、164 held code、一个合成 Job，仍为 600 秒/1 GiB/128 MiB。夹具 setup 首段 8.683 秒，旧 attempt02 为 61.331 秒。该次已终态 exit1/513.594 秒：N0 登记前被 verifier v3 的 definition-time project/source view 比较拒绝。845 源和旧 36 pins 未变，3 个观测进程已不存在，10 把锁重新取得并释放；entry closed receipt 的 hooks/owner/handles/streams/proxies 检查通过。原失败未保存具体 diff key，源码 hash 相同不能排除 stamp 或 Python binding 变化。不延长预算原样重跑。

所有已执行失败和未执行的旧 draft plan 保留。`bounded_registry_plan_01` 在审查修补后未执行；cold03 的 import-order proposal 也保存为 `fresh_n0_plan_03_pre_import_fix.json`，它不是运行记录。

开放出口：真实多 root registry、common 成功接线、Rref/三 Actual、paired commit、关闭重开与同状态重放、跨小时/192h、整体资源预算、seal、official review 和正式运行授权。

## 2026-10-18 入口检查调度与真实 common 复核

`bounded_stable_read_entry_v2.py` 的非目标读取只检查路由/lifetime；canonical open/read/第二次 fileno 保留 full，enter/第一次 fileno 为 light；receipt/lease exit 仍 full。所有原文件观察继续执行，不缓存输入/结果。`bounded_entry_v2_unit_02`：78 passed，outer exit0/2.016 秒，覆盖原 60 节点及调度、route 计数、callback 漂移、同 code/foreign globals、内层失败立即关闭、body/guard/exit 组合异常。两项独立只读 PRE_SEAL findings 已修复；无 official verdict。unit01 的 75 passed 和从未执行的 hotpaths plan01 均保留。

`entry_hotpaths_plan_02.json`：一次、零 Job/native、120 秒/768 MiB/128 MiB；实际对照如下：

| 操作 / wall seconds | 原 entry | bounded v1 | bounded v2 |
|---|---:|---:|---:|
| bootstrap identity，两次均值 | 0.345431 | 0.292378 | 0.237937 |
| training registry | 18.228170 | 1.221224 | 1.086893 |
| holdout registry | 14.824282 | 1.162578 | 1.079634 |

全部 identity 和 registry raw bytes 一致。outer exit0/51.218 秒，843 源和旧 36 pins 未变，采样峰值 241954816 bytes；两个 bounded scopes 的 hooks/owner/handles/streams/proxies 清理通过，165 个代码路径可 r+b 重开且不写入。固定顺序且有 warm-up/并发旧 chain 因素，不代表统计或整链加速率。

**真实 common 尚无收益证据。** `bounded_common_arm_plan_01.json` 只执行一次原 common._arm，复用并核验原 entry07 保存基线，不重跑旧基线。851 源、461 保存文件和旧 36 pins 未变，科学输出及完整 audit exact bytes equal。本次 **39.750354 秒**，旧基线 **36.279179 秒**；outer exit0/51.094 秒、采样峰值 204148736 bytes。一次历史对照不能确立因果回退，但也不支持提速。receipt 仍有 12678 次 canonical reads、38036 次 full checks，下一步只定位并处理真实 common 重放/校验成本。

最小 M2 路线可使用原 full-v2 target 配置新入口，保留既有合成科学 seams；整体耗时尚未闭合。v3/v4 registry 后继暂不传播到 13 个模块。完整 missing-all/每个 Actual 矩阵仍为必需；missing-one 复用已完成 Parent，额外成本是 common/completion 重验，不能误计为 Parent 重跑。真实完整链、整体性能启动审查及全部 formal gates 继续 OPEN。

## 最新修复：runtime registry 与 metadata 接线

零 Job 的 registry_dispatch_monitor_02（exit0/54.890s）定位唯一变化：真实 owner 打开后，episode_store._REGISTRY 从空 set 变为两条 writer roots；关闭后恢复，source file rows 没有变化。旧 definition guard 把合法 runtime 成员冻结，导致 cold03 误拒绝。

verifier v3 现仅在 definition view 规范此唯一 row 为原 set 身份，仍核对 module/file/set/lock、row 结构/唯一性与全部其他 rows/files，采用 nonblocking lock。私有 resource record 另保存 operation entry 的完整成员集及两条原 journal/genuine lease/key；所有 resource checks、build confirmation 和 cleanup 都要求成员与绑定不变。原 _dispatch_view、_HourScope._context 和每 prepare 16 contexts 未改。

registry_runtime_unit_02：126 passed/45.82s，outer exit0/47.188s。独立只读 PRE_SEAL 未见阻止下一有界 cold 诊断的问题。真实 owner 六节点复验 registry_dispatch_monitor_03 exit0/56.860s，定义检查全部通过，原始 view 仍观察预期 runtime 变化，849 源/旧 pins、PID、两锁和 hooks 清理通过。它没有调用 bootstrap/Job。

当前三源 closure 为 registry_sources_03_non_authoritative/patch_manifest.json，SHA256 a5835f2d6131048f2cb477d92e0053da861b6c8d29dc88600d7f3df2eb66eabf；rebuild_check_03 exit0。旧 closure02 是修复前历史字节，不代表当前源码。

**common 第一轮 39.750s 的具体原因已修复。** 原 helper 在 MetadataParseLease snapshot 后才 policy.admit；fixture 添加的重复 repo/tests 路径被规范化后，7265 次查询全部安全回退。375 个 GIL 样本来自这个 fallback 版本；139 次包含 metadata.version、95 次 leaf 为 FastPath.mtime，不能据此宣称修复后的剩余占比。

measure_bounded_common_arm_v2 已将 admission 放到 snapshot 前，保留 stock discovery 与所有 fallback 规则。bounded_common_arm_monitor_02 exit0/44.938s，arm 为 **33.794407s、hits7265/misses0**，相对错误窗口减少14.98%，相对历史正常 entry07 的36.279179s减少6.85%。这是一轮历史/固定顺序对照，不是全链加速率。

common_entry_postcheck_03_non_authoritative/terminal.json exit0：851 source/tested copies、461 saved files、33把真实锁、36 old pins、science/full audit exact bytes、owned PID absence 和 entry cleanup 均闭合，无 native/producer 重跑。

fresh_n0_plan_04.json（SHA256 32209f92f8c0d85f5f8edf5714e650363759a5536c34668e83b30b5a66622d88）已在 **600.609s 上限停止、outer exit1/child15**，不是通过。fixture 8.392s，owner_open 为 test-relative 31.735s；合成 Job 自身 exit0/whole_job_quiescent，耗时61.312s。global/bootstrap已分别持久写入3/5条记录，含normal_terminal；但 bootstrap 尚未返回，四build执行receipt、旧oracle相等断言及外部retained heads验收均未完成，不能采用保存末行推定登记成功。

fresh_n0_cap_postcheck_04_non_authoritative/terminal.json 的只读postcheck exit0：863 source/tested copies与old36 pins一致，164代码路径可r+b重开且未写入，3个观测PID均不存在，10把真实锁重新取得并释放，现场文件hash已保存。inner被预算停止，没有graceful hook-restoration/closed receipt，不能声称完成原清理断言。末次540s栈位于 fresh _HourScope._context → _dispatch_view → read_stable，其外层为 _finish_N0_terminal 的 local-retention 后再次prepare；不能由稀疏栈推断四次build进度。不延长预算原样重试。完整三arm M2及整体性能启动审查继续OPEN。

## 停止无收益路线，接回遗漏的现有路径优化

两个零solver只读mtime探针均未接入入口。held-directory query虽有局部速度优势，但对ACL/path访问失败与原pathname-stat等价性未证实；named-path API保留按路径查询后，现有七目录均比stock慢约5.9%–22.3%，停止该路线。两者均没有production hook、native solver或resource admission，原始记录分别保存在D:/h1_live_mtime_probe_01_non_authoritative与D:/h1_named_mtime_probe_01_non_authoritative。

最新saved-common与cold入口此前未激活已有CanonicalPathLease。其ENTRY07副本与experiments原实现同SHA256 f4fd83cb189ed5a05b20ecbaf72d5a29e7dc6f9746dc777d18f140bbd4aeab2d；复用既有针对性检查证据。未执行proposal03的3个helper与原plan保存于common_path_proposal_03_pre_review；修复PRE_SEAL的失败后saved核查、真实锁和metadata比较三项后，实际采用bounded_common_arm_plan_04.json（SHA256 0db56fbe8a254fe86f4f7721ff8310c8ea75fabc69d7f482e9cb4fbdb19e131e）。它固定一次原saved common._arm、0 Job/native、120s/768MiB/128MiB，以已闭合33.794407s为基线，在fixture/downstream imports前安装原pathlease。

**该接线实测通过。** bounded_common_arm_monitor_03 exit0/41.515s，arm **29.546419s**，比33.794407s减少 **12.57%**；science与完整audit exact bytes、完整metadata receipt（7265 hits/0 misses，8个pins和discovery语义）均与基线相同。path receipt为3421 hits/36 fallbacks、22 directory handles/36 canonical paths，退出后dispatch恢复、directories/paths为零。common_entry_postcheck_04_non_authoritative/terminal.json exit0：861 source/tested copies、461 saved files、33真实locks、165代码r+b无写、old36 pins、PID absence和hooks/resources全部核对。固定顺序、有旧chain并发，不能外推整链加速率。

主瓶颈是owner/phase/context嵌套校验；现有静态调用图显示每个owner check触发完整phase fingerprint，registry replay前后又重复N0准备。hour context不包含phase清单里的全部约千个依赖，尤其phase-only .md/.json，不能替代phase freshness；两个phase-static bookends及registry before/after仍有各自的变更观察窗口。cold04的9个60s稀疏样本不足以给出阶段占比：前311s才启动Job，60/120/180/240s多在implementation/vendor/raw-reader链，300s含phase fingerprint，540s含hour context。不能只凭文件数把全部成本归因于phase扫描。

为验证path接线与真实guard兼容，n0_path_owner_probe_plan_02.json（SHA256 c4d1bea3dda900fb681908ffe8b026206fb7bd68dac7c1cd2dc12059d2064d0a）仅调用原六checkpoint真实owner测试，不调用bootstrap或Job，120s/768MiB/128MiB。outer外部固定plan SHA/target/limits/roots/outputs，outer与child拒绝已有basetemp以保留工件；每秒GIL栈采样不读source/locals，不装profile/trace，并要求停止/join。它是接线与归因探针，不关闭N0/M2或整体性能审查。完整cold/整链不在该次probe范围。
