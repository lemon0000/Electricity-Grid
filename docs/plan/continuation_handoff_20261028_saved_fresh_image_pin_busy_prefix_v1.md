# C/F：image pin已走通真实busy audit的固定64前缀

2026-10-28，DRAFT_NONAUTHORITATIVE。接续[方法级交接](continuation_handoff_20261028_saved_fresh_image_pin_v1.md)，当前执行合同为[AOC8范围](staged_deliverability_c_saved_fresh_image_pin_cold_scope_v3.md)，经由[AOC6完整合同](staged_deliverability_c_saved_fresh_image_pin_cold_scope_v1.md)与[AOC7修复](staged_deliverability_c_saved_fresh_image_pin_cold_scope_v2.md)承接。root唯一writer，独立代理只读PRE_SEAL；无official verdict/receipt、production seal或run authority。宽goal保持active，完整F仍未完成。

## 当前已完成的边界

image-pin1仅在单次_image内复用相等exact bytes的pin，保持每位置fresh dict、完整tuple/JSON/digest和所有guard检查。既有9/9方法证据及AOC4的14/14、AOC5 terminal4/4按exact pins复用，本轮新unit0。core22/probe19/parent19只做6处literal迁移，raw/AST变换相等；helper image-pin1、policy、namespace timing1和Source49不变。迁移、复用证据19项、历史终账4项、709个registration inputs及checkpoint脚本pin均进入机器绑定。

AOC8新size/codec、登记、非官方PRE_SEAL、startup、profile、strict64、saved与checkpoint全部accepted。实际命令 **29972/30000 UTF16**，minified prefix4389B；payload逐字节（注释空格化）、含位置AST/CodeType、prefix token/AST、实际argv/zdict/EOF/no tail重核，不声称prefix列位置或CodeType未改变。startup画像重新发现且与本transport/env/helpers绑定，profile33196B；size与registration的108项条件runtime来源表严格相等。

唯一获准的actual adapter import路径（调用上限1次）已在真实busy audit中走过固定64个原policy分类并放行的open尝试：10帧为0/1/8/16/24/32/40/48/56/64；terminal=prefix_complete，entered=passed=observed=64，rejected/error=0，active/inflight=false，last_incomplete=null。新_image局部def/closure没有在这段路径触发guard/reentrant/metadata拒绝；没有全事件记录器，`all_unselected_events_verified=false`。第64物理open未执行，前63个尝试也不宣称I/O完成。

driver audit charge **3.198652300001413/8s**；parent capture **2.0242666999984067/7.1883251999970526s**。child exit1，status=failed，primary精确为`AuditCensusStop: diagnostic_prefix_complete_64`；secondary仍为`LocalRuntimeUnresolved → BootstrapImportUnresolved → ValueError(policy_terminal)`完整链。runtime=UNRESOLVED、boundary=FAULTED、runtime_was_live=false、import_profile=null、adapter return未观察到。父端接受的是预定停止的严格前缀诊断，不是完整import成功。

self HANDLE各close一次，DLL directory close返回，resource=CLOSED；父端HANDLE/stdin/pipes与writer/readers终态，无kill、cleanup、reader error或截断。stdout4437B/stderr10083B原base64及pins保存。cold RSS未测，不能拿旧unit峰值代替资源准入。实际prefix snapshot−start **0.14729410000290954s**；audit inclusive **0.05108929999551037s**，entry **0.05010259999835398s**，image_digest **0.025308300013421103s**，cache **0.013144500000635162s**，cache从11到20项、新增9。inclusive包含entry，entry包含各分段，不能相加或把残差叫I/O。与AOC5单次数据对照不能证明cold/完整import提速；方法16.6%收益仍只属于原固定fixture。`candidate_adopted=false`。

## 本轮失败和诊断全部保留

| root | 文件/字节 | 真实终态 | 新增static秒 |
|---|---:|---|---:|
| aoc_v6 | 8 / 381504 | size通过；register origins不等拒绝；cold0 | 1.9975649999978486 |
| origin_order_v1 | 2 / 131973 | 两个只读metadata child成功，但未复现差异 | 1.5583934000023874 |
| origin_order_v2 | 2 / 134393 | 补齐UTF16步骤后复现唯一新增codec叶 | 1.3953773000030196 |
| aoc_v7 | 17 / 712798 | startup通过；profile仅阶段1s超帽拒绝；audit0 | 6.240888099993754 |
| aoc_v8 | 22 / 797122 | 新startup与strict64、saved/checkpoint全部通过 | 10.336638699991454 |

以上目录完整前缀均为 `results/tables/staged_rts24_saved_fresh_`，后缀均为 `_non_authoritative`。已有源码、inputs及各root实际保存的stream/失败/终账均冻结；不能原地修改或重跑其CLI。所有Source49及更早AOC1/2尺寸拒绝、AOC3 float失败、旧120/540/import8MiB超帽与25条既有不接受记录继续保留。

AOC6 register在采样前执行`list2cmdline(...).encode('utf-16-le')`，而size在采样后编码；冻结CLI在`origins==size['conditional_runtime_origins']`断言处拒绝，registration_failure保存AssertionError与0.8061634s。origin v1漏了这一步，观察未复现，不能改写为成功解释；v2补齐后，size仍exact match，register唯一added=`encodings.utf_16_le`、removed/changed均空。AOC7在runtime_leaves公共入口统一预载该模块，保留来源表完整相等。该source1037B/cache2151B分别以3aedaf3e...fd80 / 6bdf0aed...2c1绑定，仍是条件TCB叶，独立TCB认证false。

AOC7 profile逻辑产物已写、error=null，但charge1.0872899999958463>1，外层phase accepted=false，所以未启动audit。拒绝checkpoint仅accepted metadata。AOC8依据此实测，把原22s总帽的最后1s余量分配给profile（1→2）；audit8、全部科学/检查阈值与总帽不增，原失败费用不退款。本次两个不接受记录使历史计数25→27；两个metadata诊断accepted不增加计数。

## 预算和机器入口

AOC8阶段charge：size **0.7754692000016803**、register **0.7315793999950984**、PRE_SEAL **1.190527300001122**、startup **1.6622871999934432**、profile **0.9723152000005939**、audit **3.198652300001413**、saved **1.1738948999991408**、checkpoint **0.6319131999989622**。static **10.336638699991454/22s**、新unit0；root22/24文件，797122/4MiB。

全历史static **253.99434230000338**、pytest **366.48897970000326**、unittest **69.47058930000276**，总 **689.9539113000094s**，不接受 **27条**。总账直接取每个最新前驱，不重复加诊断费用。编辑/审查/Git、既定Python初始启动和最终记录写入不计capture，不是完整wall，无模拟小时推进。

恢复先读AOC8 `checkpoint.json`、registration、size_admission、helper_snapshots、pre_seal_findings、各phase exit、`saved_report.json`与`probe_import_discovery.receipt.json`。saved直接重放并携带exact64 `audit_validation`，checkpoint再次相等回读；receipt仍保留完整primary/secondary与原始streams。source epoch为 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**。

归档先核每phase精确文件集，单writer给exit/checkpoint预留槽与字节；metadata配额wrapper不改parent磁盘逻辑或child policy。若派生receipt超帽，只保存完整raw streams/父端元数据及派生结果pin并拒绝，不伪称超帽派生JSON已保存。本次未走该超帽分支，不能把静态保全设计称为真实超帽故障实测。

## 接下来的实际门槛

当前堵点已移回**完整B_S import闭合**。下一独立后继应先写允许import完成的有限scope：确认全路径调用量、M/D认证、NumPy政策、adapter直接图/retention、Source书挡、输出/资源/失败关闭成本，再决定一次有依据的有界完整import诊断。当前helper在64处主动stop，不能直接沿AOC8命令获得完整import。之后仍须独立固定OBSERVED profile，验证正常LIVE及故障矩阵，再连接真实producer/retained owner/Job/bootstrap、ACK/issuer/permit、quiet/返回与父端采用；固定64并不关闭这些门槛。

E/U、独立TCB/native、完整runtime/P1/role/permit/F/科学/资源/正式/run authority全部false。39项并行文稿/图件/文献dirty保留；发布仅本轮scope、所有失败/诊断/成功记录与四导航新增段，共享导航正文保持原工作区修改。远端提交号以发布后的实时读回为准。
