# B_S image pin：真实busy audit固定前缀后继

2026-10-28，DRAFT_NONAUTHORITATIVE。起点bacacbaa663fe7e08497cacc27a1881548f3aeb5，接续[image pin方法交接](continuation_handoff_20261028_saved_fresh_image_pin_v1.md)。9/9方法验证、new/old总0.8341837/中位0.8478925仅为必要方法证据；本scope解决真实busy audit中新增局部def/closure是否导致固定前缀guard故障。root唯一writer，独立只读PRE_SEAL，无official verdict/receipt/seal或run authority。

独立AOC6：core20/probe17/parent17只做8处literal occurrence机械迁移。core19→20的AOC5→6为2处，probe16→17为1处；parent16→17的OUT、CORE19→20、PROBE16→17各1处，BS census4→image_pin1为2处（manifest path与取pin路径）。记录旧新raw pins、各needle唯一次数及替换后逐字相等。复用image-pin1 exact9/9、AOC4 exact14/14及AOC5 exact terminal4/4，不为机械迁移重跑镜像测试；新unit child为0。候选helper本身、namespace timing1、policy与Source49全部原字节复用。

完整DAG：前驱终账与全部inputs重开 → size/codec/manifest准入≤2s → register≤2s → PRE_SEAL≤1s → 新startup discovery≤3s → profile admission≤1s → 唯一获准的actual import路径固定64前缀≤8s → saved≤2s → checkpoint≤1s。static≤22s（最坏20s+2余量）、unittest0、总≤22s；最多两个串行cold child，startup ENTRY0，actual ENTRY≤2、adapter attempt≤1。0模型/Highs()/solver/P1/hold/capture/replay/OwnedChild/Job/实际F。失败或超帽create-only保存并停，不重跑已执行字节或扩帽；可用原预留metadata阶段保存拒绝终账。

优化决策：局部pure-bytes pin去重已达到预定方法收益门槛；本轮只验证实际接线，不扩展跨audit缓存、event采样器或policy豁免。前缀仍固定64个原guard放行的open尝试，observer在guard后，第64物理open不发生。原census帧/primary/secondary/收尾合同保持，watchdog关闭。正常selected open能在真实busy hook中走过且无reentrant/metadata故障，只支持这段固定路径；没有新增全事件记录器，因此不能宣称不存在所有未选择事件或获得完整事件序列。

size先核实际prefix minification token/AST、最终prefix=zdict=argv decoder来源、payload注释空格化后逐字节/含位置AST/CodeType、131072解压帽/EOF/unused/tail与最长完整argv≤30000 UTF16；不能沿用29972。核实际manifest的新helper path及其独立raw pin。transport变化后必须重新startup/profile，绑定registration/env/transport/helpers和全部startup disk observations。controller登记其实际stdlib disk source/cache条件叶，保持independent TCB false。旧root inventory严格等于其终账map加终账本身，新root size前仅driver/policy，register前仅driver/policy/size。

root `results/tables/staged_rts24_saved_fresh_aoc_v6_non_authoritative` ≤24文件/4MiB：沿用4MiB字节帽，因去掉四份unit工件，预计22份加2份metadata余量，文件帽较旧26收紧。stdout131072/stderr32768，census≤12帧×2048且总≤24576，profile≤1MiB，module/cache4096帽不变，RAM只观测。每case父端只允许一次Popen，deadline后kill并收尾；最多两个串行case且不重试。复用9/14/4证据各exact pin与元数据记录，包含所有artifact/input、admission、report、metrics与旧终账，不把复用称新执行。

prefix accepted矩阵固定为：恰好十帧0/1/8/16/24/32/40/48/56/64，terminal reason=prefix_complete，active/inflight false、last_incomplete=null、passed/entered/observed64、rejected/error0；primary精确为AuditCensusStop(diagnostic_prefix_complete_64)，secondary精确承接AOC5既有LocalRuntimeUnresolved→BootstrapImportUnresolved→ValueError(policy_terminal)链，不允许新guard/reentrant/metadata fault。child未kill，有self-close witness、self HANDLE各close1、DLL close返回、resource CLOSED、runtime UNRESOLVED、boundary FAULTED、runtime_was_live=false、import_profile=null；父端HANDLE/stdin/pipes、writer/readers终态，无cleanup/error/截断。import提前return、少/重/跳帧、timeout/kill或新异常均accepted=false并保留；未达前缀不得补算。`all_unselected_events_verified=false`及`candidate_adopted=false`在登记和终账中保持。inclusive各桶有包含关系，不相加；单次新旧前缀对照不能证明全import提速或旧超时根因。

控制器在每phase前核精确文件集并为本phase exit（16KiB）及checkpoint（64KiB）保留文件槽和字节。所有自身metadata写入先检查单文件与root配额；size≤256KiB、snapshot/registration各≤512KiB、transport≤32KiB、saved≤64KiB，其余metadata≤16KiB。case启动前按plan≤64KiB、receipt≤1MiB和discovery profile≤128KiB先做最坏空间准入；profile是未压缩且canonical的child stdout子树，因此128KiB继承既有stdout帽，同时profile admission仍显式核≤1MiB并保存实值。parent源码仍仅literal迁移；controller给parent metadata save加配额wrapper，不改child policy。若派生receipt超过1MiB，保存原始stdout/stderr、全部父端顶层元数据及超帽派生result/receipt的pin，省去可重算的result并判失败；未持久化的超帽派生JSON不冒充保存原字节。每case仍只有一次Popen，失败时不重启；这些是专属root的单writer存储约束，不认证并发外部文件写入。saved直接重放exact64矩阵并保存validation，checkpoint逐项回读相同validation。条件runtime origins在size与registration间严格相等。

前驱image-pin终账累计static232.46547980001492、pytest366.48897970000326、unittest69.47058930000276，总668.4250488000209s，不接受25条。新账不重置所有失败、旧120/540/import8MiB超帽。Source49 epoch acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875及49份raw不变。编辑/审查/Git、Python初始启动及最终记录写入不计capture，不是完整wall，无模拟小时推进。39项并行dirty保留。

E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false。即使固定前缀通过，OBSERVED/LIVE、完整B_S/NumPy/adapter图/retention/Source书挡、真实producer/permit/父端采用与F仍OPEN，整体F性能审查未完成。
