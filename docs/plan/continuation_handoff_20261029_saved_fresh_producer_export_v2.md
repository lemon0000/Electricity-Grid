# F：producer 数据交接、延后bundle与失败清理检查点

2026-10-29，DRAFT_NONAUTHORITATIVE。宽goal“持续推进”保持active，完整F未完成。承接[权限检查点](continuation_handoff_20261029_saved_fresh_p1_permission_v2.md)，本轮补齐关闭前的数据保留、可逆packet、延后bundle、创建bootstrap独立cleanup和quiet后的纯数据重开。root唯一writer；retained_lifecycle_review完成独立只读PRE_SEAL，未形成official verdict、receipt或production seal。真实Source49目标模块、P1内容、Native owner、角色、模型、solver执行均0，NFC12未重跑，新增模拟跨度0h。

## 当前源码与验收范围

- [LC6](../../experiments/staged_rts24_saved_fresh_retained_producer_v6.py)在G3成功cleanup前捕获packet；cleanup后再比较，完成wire/report canonical及容量检查，才清除live references。成功保留packet、阶段pins/clocks；export、late-wire、post-close或reset失败保留sticky carrier、原primary/secondary和原引用证据。内嵌codec由[export变换v2](../../experiments/staged_rts24_saved_fresh_producer_export_transform_v2.py)精确派生。
- [packet v2](../../experiments/staged_rts24_saved_fresh_producer_packet_v2.py)按原tuple/serialized-list stage pin验证，闭合G0/G2/G3与原expectation/context/image pins，保持原180秒invocation区间。精确schema/字段/gates、49 source、683 inputs/2950863B、metadata身份/祖先目录、duplicate JSON及压缩终态均受检。
- [Helper7](../../experiments/staged_rts24_saved_fresh_producer_bootstrap_v7.py)的after_import只READY。B_S关闭后仍在IMPORTING时须prepare_consumer，再finish_import到profile-matched LIVE/PREPARED，才可请求固定issuer并finalize bundle，LC随后持有唯一slot。[deferred变换v2](../../experiments/staged_rts24_saved_fresh_deferred_bundle_transform_v2.py)保留caller admission=None边界。public permission v1的issue/verify/claim仍始终拒绝。
- [Coordinator2](../../experiments/staged_rts24_saved_fresh_complete_producer_v2.py)要求创建bootstrap在ADOPTED、DISABLED/NEW、admission=None时保存原close及same-state revoke。固定permission raw/revoke code、空builtins、exact native put及执行后DENY/CLOSED均受检。bundle发行/构造、prepare返回前及后续run/G2/G3/close都在cleanup边界；未占槽保持PREPARED，已生成producer保留LC wrapper及其secondary/runtime_close。完整结果先canonical/容量检查，后release bridge，成功返回纯数据。
- [Parent2纯数据重开](../../experiments/staged_rts24_saved_fresh_producer_parent_reopen_v2.py)先核codec源pin，再exec已核的同一raw。它验证quiet观察、closed producer/permission、完整packet关系和False gates；physical_parent_P1_reads=0。真实Parent仍须由held child/process/drain receipt绑定PID、stdout raw pin和writer/readers/pipes终态，再完成独立683文件SHA核验。

schema链为detached packet **v2** → retained observation **v3** → complete producer data **v2** → parent data replay **v2**。原v1 codec的dict-stage格式与新pair格式不兼容，旧字节保留。Core42/Loader3/Probe40/Parent39仍是上一检查点的unadmitted construction路线；Helper7与Coordinator2尚未接入真实bootstrap/Native。consumer不能通过callback、bool、manifest、profile或release数据取得P1权限；真实issuer与成功发行诊断许可的observation必须使用获批后继。

packet会携带683项pins/metadata及53个P1文件已解析形成的outer/trusted、6 bindings、expectations、历史指标、21 evidence_refs等原expectation/context派生内容，还含绝对路径、允许的environment字段、Python版本和文件身份。683文件raw payload不导出。未来真实输出授权须覆盖这些派生内容及本机元数据。本轮ordinary只用合成字段。raw packet1MiB、还原输入各2MiB、wire128KiB、complete对象256KiB均为fail-closed帽，真实代表尺寸仍未知；完整child行的transport至少需256KiB+1，旧128KiB路线须经版本化更新与准入。

## 已保留的失败与通过证据

[v1合同](staged_deliverability_c_saved_fresh_producer_export_scope_v1.md)唯一unit出现69组start/end进度，缺最终report，stderr观测46221B超过32768B，触发kill/truncation及capture_error。不得计为测试通过。原因一是原LC evidence pin为tuple/JSON list，codec却要求dict；原因二是expiry fixture全局替换stdlib time.monotonic，碰到LC新增time依赖的TCB完整性检查。原代码、测试、scope、原流和费用均冻结保留，没有在v1重试。

v1 root：`results/tables/staged_rts24_saved_fresh_producer_export_v1_non_authoritative`，4文件812661B；CP9220B、SHA **65f3050be22825b955415280b0151b8479e6223a756ff29589eb2410e23ffa50**。register1.0121395000023767s、unit拒绝7.483748499973444s、checkpoint0.558679999987362s，总9.054567999963183/40s。accounting_complete=true、diagnostic_accepted=false；CP accepted表示账务保全。此时累计1273.8435644999656s、49条拒绝。

[v2合同](staged_deliverability_c_saved_fresh_producer_export_scope_v2.md)改为严格原pair、同步schema、private permission time proxy及test52的serialized index1；保留原69项断言并增加test70。唯一70项由31生命周期+17权限+22数据/失败/顺序组成，覆盖完整private链、actual Helper release、独立revoke、retire verifier坏、LC secondary、late wire/complete cap/JSON失败保refs及固定issuer拒绝callback。

v2实际70/70，0failure/error/skip，runner **8.054s**、outer **10.660003199998755/12s**，child帽10秒保持；142 canonical frames包括完整最终report。rc0、capture_error=null，stdout24096B、stderr12184B，零kill/truncation/reader/cleanup错误，process handle、pipes、readers均终态。605个native memory samples：parent peak33579008B、child102752256B、两者peak和最大136331264B、private和最大102678528B。该peak和为取样观测，continuous_bound_verified、combined_retention_verified及resource_admission仍false；128MiB整链retention尚未验收。

独立PRE_SEAL逐pin核1358 inputs/69692331B、235 archive/25455480B及12 own，bad0；v1全部source/root pins保持。saved原始stdout/stderr及memory/terminal重开接受。各阶段：register0.9672651999862865s、unit10.660003199998755s、pre_seal1.2523874000180513s、saved1.1793794999830425s、checkpoint0.5989146000065375s，总 **14.657949899992673/40s**，static3.9979466999939177s、unit10.660003199998755s。未扩大任何阶段、stdout/stderr或memory帽。

v2 root：`results/tables/staged_rts24_saved_fresh_producer_export_v2_non_authoritative`，6文件798029B；CP11133B，SHA **898de661acd09bbbce60fa80e8ddebe44f8c8e9476870758abe04ad148cd200c**。accepted/accounting_complete/diagnostic_accepted均true，acceptance_scope=`producer_detached_data_cleanup_and_deferred_bundle_units_only`。registration709947B/SHA **6dae9d3205cbe2b199c4f077b311b8b2664bd96075c7113c759c2df269ba3c3c**；unit50801B/SHA **06697c8f71938294a90771515c90d688d462439e406597af0b751acbf5fd8f0e**。

下一账源固定该CP：累计static **624.0365631999841s**、pytest **366.48897970000326s**、unittest **297.9759714999709s**，总 **1288.5015143999583s**，拒绝 **49**。本轮两包合计23.712517899955856s，旧费不退款、剩余不转用。后继完整继承为expanded1358加当前root6扣driver重叠1，即1363 inputs；archive241文件26253509B。新own集合必须显式union并核完整历史，不能只核Source49/NFC12子集。

## 完整F下一步

目标仍为获批外层真实诊断授权 → 同LIVE owner完整producer → held Parent quiet后独立内容重开采用 → whole-workflow wall/RAM/storage准入。先准备具体outer授权创建点和固定source/scope、版本化Loader/Core/Probe真实接线、独立startup/import profiles及Parent quiet/P1逐SHA实现；在创建bootstrap内调用prepare_coordinator_cleanup，遵守IMPORTING prepare_consumer → LIVE/PREPARED bundle → LC claim/run/G2/G3/close，成功后不再consume_once。发行后bundle/prepare失败必须使用独立cleanup，publish/audit失败保留证据并结束该attempt。

实际执行前按agent.md第9节固定完整DAG、调用量、预算及专项授权。旧完整producer107次静态基线、构造43次图合同均不能替代outer/P1/fault/parent成本；新路径还包含2次packet_capture、producer3次packet_restore、parent解压/还原2次及真实publication。真实包尺寸、P1 I/O、guard兼容、父端逐文件核验和昂贵失败路径仍需代表证据。当前public issuer仍DISABLED，Source49 closed SavedLaunchIssuer不能复活为本诊断许可。

Source49 epoch **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**、NFC12全部16文件及CP **bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de**保持；原39项并行worktree字节、B1–B3、原P2七输入及全部失败/冻结工件保留。发布前最终3295次pin比较覆盖1450个唯一文件，bad0；12个新增文档本地链接有效，39项并行SHA一致。现场process快照仅VS Code Jedi35552，无formal/native/solver活动。四个共享导航只在index发布前置段加原HEAD正文，worktree并行字节不改；最终remote hash/index/39项终态以发布后现场读回为准。

role/permit/science/resource/formal/run/F gates均false，宽goal保持active。新对话从本交接、agent.md第7–9节和最新Git/process/pin快照继续；不得重跑NFC12或据本检查点启动真实Native/P1路线。
