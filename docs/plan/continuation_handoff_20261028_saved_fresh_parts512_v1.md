# 优化helper的真实512窗口完成，image构造成为下一候选

2026-10-28，DRAFT_NONAUTHORITATIVE。起点`4dc626abb4e3197e5b5020289fa546e6b809370d`，承接[cache方法/full失败交接](continuation_handoff_20261028_saved_fresh_cache_parts_full_timeout_v1.md)，按[本轮范围](staged_deliverability_c_saved_fresh_parts_census512_scope_v1.md)执行。root唯一writer，既有reviewer只读PRE_SEAL，无official verdict、production seal或运行授权。宽goal继续active，完整F未完成。

## 本轮实际终态

PFC1的size/register、8/8 unit、PRE_SEAL、startup/profile、唯一观察窗口、saved/checkpoint全部accepted。command **29972/30000 UTF16**，payload字节变换、位置AST和CodeType等价通过；Source49原49份raw不变。

真实终态为 **prefix_complete（512）**，不是自然返回：`finite_terminal_complete=true`、`prefix_complete=true`、`adapter_import_return_observed=false`。10帧passed为 **0,1,64,128,192,256,320,384,448,512**。每帧九bucket计数=passed、固定start、cache增长公式、phase非降、final↔child report一致，错误/拒绝0。第512次guard-passed观察后在该次physical open前主动停止；方法测试证明窗口内最多511次physical open，不能解释为全程序总打开次数。

child exit1/status failed是预设`AuditCensusStop: diagnostic_prefix_complete_512`；primary及完整secondary与原64序列化链仅做固定stop消息替换，`LocalRuntimeUnresolved → BootstrapImportUnresolved → ValueError(policy_terminal)`保留。runtime **UNRESOLVED**、boundary **FAULTED**、resource **CLOSED**、self HANDLE各close1、DLL关闭、namespace alias移除。parent HANDLE/stdin/pipes/writer/readers全终态，drain_reason=null、killed=false、cleanup/reader/writer errors空；stdout4443B/stderr10123B完整未截断。

父端case charge **3.1220558999993955/cap7.029757099997369s**，外层audit charge **4.603723300002457/8s**。direct child peak working set **81080320B = 77.32421875MiB**、error=None，仅为这个前缀的观测，不是完整import/F资源准入。source_bookends=2、retained_modules=0，M/D observed/authenticated仍0，optional/blocked Popen各1、internal introspection6。没有adapter返回、完整B_S、OBSERVED/LIVE或producer证据；保留全部false gate。

## 新的真实计时证据

窗口begin→final snapshot为 **1.0149127999975462s**，cache **11→62项（新增51）**。这些是同一次受控前缀的inclusive计时，不能相加重复层级：

| 桶 | 累计秒 | 比例 |
|---|---:|---|
| audit_body_inclusive | 0.5038959000230534 | 选定open audit层 |
| entry_total | 0.4956265999790048 | 窗口48.83% |
| image_digest | 0.29295780002576066 | entry **59.11%**、audit58.14% |
| cache | 0.11115910005901242 | entry **22.43%** |
| ownership | 0.03938839992042631 | 原检查保持 |
| identity1 | 0.034590399962326046 | 原检查保持 |

同run的first256计数处cache=48项、cache累计0.034772700018947944s、image0.12921680003637448s。256→512段新增14个cache项。旧未优化256与本run的progress频率、缓存/机器状态等不构成受控速度对照，因此不据它们给出真实链加速倍数；上一方法fixture的0.199比率也不能替代完整import实测。

新证据支持优先审查**image构造中的重复工作**。源码位置为本helper的`BootstrapImportBoundary._image`和`digest`：当前每次创建包含大量id值的fresh tuple，并使用已有call-local bytes pin去重；digest再做canonical JSON与SHA。tuple、id、JSON和SHA子项没有独立计时桶，它们只是源码分解后的候选假设，不是本次计时已完成的归因。下一候选尚未实现，不应先假定其中某项就是完整timeout原因。任何优化仍须保留fresh bookend、identity/defaults/ownership/source检查、独立image等价oracle和异常顺序，并先固定有限成本/次数再验证。

## 实现、两个mode和证据边界

新helper由纯source constructor `parts512_transform_v1.py`生成：从原census256只对五个函数做登记literal/schema/schedule变换，active finish分支增加单条held boundary stage刷新；_check_cache完整AST取已验cache-parts方法。其余完整AST及所有header不变。core27/probe24只迁移同长度root2/1处；parent24从parent21按明确路径与新mode validators生成，helper/parent完整raw在size与register重放绑定，不能仅依赖自选input pin。

验收预先允许512到达或importer在512前返回这两个finite mode。自然返回必须完整return stage、terminal frame、真实child报告、异常链与关闭见证；wrapper会立即主动stop，仍不进入M/D认证、adapter roots和OBSERVED。**本轮真实只执行512 mode**；自然返回、完整record经compare_child、import_error拒绝、phase0/1/2、有限输出/primary与metadata故障等由8个合成unit验证，不能称自然返回已真实发生。fake selected-open总量保持≤4096；原10项cache/full方法证据按绑定复用，不重复计为本轮测试。

## 预算与恢复

root `results/tables/staged_rts24_saved_fresh_pfc_v1_non_authoritative`：**25文件/994129B**，上限30/4MiB。1个unit child+2个串行cold child全部终态，没有新失败/重试/延长。checkpoint写后不再往root追加或改写。

| 阶段 | charge秒 |
|---|---:|
| size | 1.0041937999994843 |
| register | 1.2237930999981472 |
| 8项unit | 3.1825631000028807 |
| PRE_SEAL | 1.4528146000011475 |
| startup | 1.9748615000062273 |
| profile | 1.2977213000049233 |
| audit window | 4.603723300002457 |
| saved | 1.2320405999998911 |
| checkpoint | 0.7726185000065016 |

scope static **13.56176670001878/22s**、unit **3.1825631000028807/6s**、总 **16.74432980002166/28s**。累计static **310.80556120004917**、pytest **366.48897970000326**、unittest **80.17350020000231**，总 **757.4680411000547s**，不接受仍 **30条**。所有旧失败和费用保留，旧scope余量不重置；编辑/审查/Git、Python初始启动和最终记录写入沿原口径不计capture，非总wall、无模拟小时推进。

恢复先读本root checkpoint、registration、size内migration、source transform、unit报告、PRE_SEAL findings、各phase exit、saved_report和probe_import_discovery.receipt。登记863项输入，继承最新ful_v3的831-input祖先与HISTORY9，包含旧失败/快照。Source49 epoch仍 **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**。成功saved/checkpoint只接受这个有限观察窗口；`cold_import_acceptance_complete=false`，没有关闭完整B_S/F门槛。

下一步按新分段证据审查image重复构造的可证明优化；完整import及512以后的分布仍未知。之后仍需OBSERVED profile、LIVE成功/故障矩阵、真实producer/owner/Job/bootstrap、ACK/issuer/permit、quiet/返回和父端采用。E/U、独立TCB/native、完整runtime/P1/role/permit/F/science/resource/formal/run authority全部false。

39项并行文稿/图件/文献dirty保持；Git只发布本轮scope与四导航前置段，原正文不覆盖。远端提交号以发布后实时读回为准。
