# C/F：image pin局部去重方法验证通过，待真实audit后继

2026-10-28，DRAFT_NONAUTHORITATIVE。接续[64-open前缀](continuation_handoff_20261027_saved_fresh_audit_census_prefix_v1.md)，本次实施合同为[image pin范围](staged_deliverability_c_saved_fresh_image_pin_scope_v1.md)。目标仍active；root唯一writer、子代理只读，无official verdict/receipt、production seal或run authority。F仍未完成。

## 实际改动与等价范围

独立后继 `experiments/staged_rts24_saved_fresh_bootstrap_import_image_pin_v1.py` 与冻结census4相比，仅`BootstrapImportBoundary._image`的AST改变。每次调用创建局部memo，仅exact bytes按完整值复用原pin；各位置以字面量复制返回独立dict。非exact bytes沿原pin处理，不进入memo；调用返回后无保留状态。原image tuple、字段/id读取和分支顺序、所有audit/identity/metadata/cache/finder/ownership/Source检查保持。完整canonical JSON与最终SHA仍每次执行，没有缓存整个image、最终commit或live metadata。

依赖是固定纯pin/sha与不可变bytes；这是输出等价，消除重复pin调用会改变人工注入第N次调用故障的轨迹，不宣称所有副作用/故障序列相同。memo无新slot/global，fresh dict没有引入builtin dict读取。Source49与旧helper/root全部字节保持。

9/9新unit通过，0 failure/error/skip，覆盖冻结v4真实_image的完整tuple/canonical bytes/digest oracle、各旧image字段与phase矩阵、相邻调用变化、distinct-but-equal/空/大bytes、非exactbytes与mutable buffer、pin节点无别名、调用顺序/首次unique故障/每次清空、完整helper code/default proof、metadata/finder与stale commit逻辑。set/del为直接调用实际classifier，未安装进程audit hook；kw字典漂移、finder default漂移和entry拒绝直接执行真实bookend。本轮没有重跑旧14或其他历史回归，不把新9项扩写成完整runtime验证。

## 成本结果与原始证据

root为 `results/tables/staged_rts24_saved_fresh_image_pin_v1_non_authoritative`，终态 **13文件/424927B**，在16文件/2MiB内。恢复先读registration、helper_snapshots、unittest.exit/report、metrics、pre_seal_findings与checkpoint.exit；四phase exit与saved snapshot均已完成，不得重跑或覆盖。

三轮各128次image+digest，顺序old-new/new-old/old-new，方法fixture为global24/own24/attribute23行。old三轮秒数 **0.01112239999929443 / 0.010820299998158589 / 0.012275900000531692**；new **0.009430599995539524 / 0.009423600000445731 / 0.00969039999472443**。new/old总时间比 **0.8341837477977125**、中位数比 **0.8478925408309151**，均达到预定≤0.95，约为16.6%总时间与15.2%中位数下降。空binding小形状各20次，old0.0004415000003064051、new0.00032389999978477135；原值全部保留，不追加测量。

这仅为固定合成方法fixture的成本证据，不是cold或完整import收益。AOC5原64前缀的image_digest 0.0284853s不能直接乘此比例当作整链提速；原完整import未返回状态不变。`candidate_adopted=false`，仅具备设计独立cold后继的必要方法证据。

unit capture returncode0、error null，stdout0B、stderr1335B完整保留，9项逐项ok；无kill、cleanup、reader error或截断，HANDLE关闭，pipes/readers终态。peak working set **43839488B**仅是此unit子进程观测，不是cold RSS/资源准入。

独立PRE_SEAL逐项重算645个input pins、4个helper pins、原始stream pins与helper snapshots均一致，must_fix_open=[]。执行前发现的旧root额外文件被吸收风险，已在登记前修为OLD精确24项加checkpoint、OUT精确仅driver；新stdlib输入遗漏也在执行前修复。登记预载固定stdlib根，保存137模块来源：39 built-in、19 frozen、79 conditional disk叶（76有cached pin）。source/cache都纳入input并在unit前后重哈希、重建同一origin表。它们是已记录的条件TCB，`independent_tcb_authenticated=false`；没有借此认证native或外部truth。

## 预算与失败账

| 阶段 | charge秒 | 帽秒 | 终态 |
|---|---:|---:|---|
| register | 0.2830321000001277 | 2 | accepted |
| unittest | 1.8790272000042023 | 5 | 9/9 accepted |
| pre_seal | 0.47377250000135973 | 1 | accepted |
| saved | 0.33772599999792874 | 2 | accepted |
| checkpoint | 0.335712500003865 | 1 | accepted |

scope static **1.4302431000032811/8s**、unittest **1.8790272000042023/5s**，共 **3.3092703000074835/13s**。累计static **232.46547980001492**、pytest **366.48897970000326**、unittest **69.47058930000276**，总 **668.4250488000209s**。不接受仍 **25条**，AOC1/2命令拒绝、AOC3 float失败与所有旧失败、120/540/import8MiB超帽保持；新scope不重置旧账。编辑/审查/Git、Python初始启动及最终exit写入不计capture，不是完整wall，无模拟小时推进。

## 下一步

先核Git/process及本root terminal原bytes，再登记真实audit后继的DAG、次数、command/存储/阶段/总帽。最小迁移可用同长度AOC6 root，另立core20/probe17/parent17；core与probe迁固定OUT，parent迁OUT/CORE/PROBE，并同时更换BS helper path与取pin路径。复用本轮exact helper与9/9证据，不能只改路径而漏源码pin。新版本名称目前只是后续设计，尚未创建或运行。

同长度root不保证压缩长度相等：必须重新完成minified prefix→zdict→actual argv decoder、payload逐字节/含位置AST/CodeType、prefix token/AST、解压EOF/tail及最长argv≤30000准入；原29972不能沿用。transport变化后重新startup discovery/profile admission。真实busy audit中的新增局部def/closure行为尚未验证；旧_image已有genexpr也不能代替该验证。后继先保持固定64上限及原policy，核实际selected open能走过而无reentrant/metadata故障、10帧、原primary/secondary和资源终态；记录器不能自行读敏感code/frame、启用trace/profile或豁免policy。

本轮cold/ENTRY/adapter/F均0；下一轮固定前缀也不证明完整import、OBSERVED/LIVE、producer或F。完整B_S/NumPy/adapter图/retention/Source书挡及正常LIVE、真实角色/permit/父端采用仍待后续闭合。Source49 epoch **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**及49份raw不变。E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false。

39项并行文稿/图件/文献dirty保留；发布只含本scope、所有本轮记录及四导航新增段，共享导航正文保持原工作区修改。远端提交号以发布后的实时读回为准。
