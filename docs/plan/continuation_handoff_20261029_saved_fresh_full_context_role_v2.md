# F：full-context role 八组合成机制验证检查点

2026-10-29，DRAFT_NONAUTHORITATIVE。用户已恢复推进 F；本次完成原[WIP 交接](continuation_handoff_20261029_saved_fresh_full_context_role_wip_v1.md)的八组修补准备、普通验证与独立只读 PRE_SEAL。完整 F 尚未完成。root 唯一 writer，未生成 official verdict、review receipt、production seal 或真实运行权限。新增模拟跨度 **0h**，NFC12 未重跑。

## 本次验收与边界

最终使用 [runtime v2](../../experiments/staged_rts24_saved_fresh_full_context_role_runtime_v2.py)、[26 项测试 v2](../../tests/test_staged_rts24_saved_fresh_full_context_role_runtime_v2.py)、[设计 v2](staged_deliverability_c_saved_fresh_full_context_role_design_v2.md)与[scope v2](staged_deliverability_c_saved_fresh_full_context_role_scope_v2.md)。八组具体修补与方法映射见[设计 v1](staged_deliverability_c_saved_fresh_full_context_role_design_v1.md)。

| 组 | 已验证机制 |
|---|---|
| authority | 原六内部 effect 门与 public binding 均先无条件拒绝；AST 副本只接精确固定 fixture 的 namespace/CodeType/owner/clock/cleanup packet |
| role/context/launch | owner/role/context/receipt/template join、closed request 及早于原 context 的外层 deadline 拒绝 |
| partial launch | 先强持 create 原结果与 primary；capture 失败交付该实际结果；空返回/恢复失败保留 unresolved，不猜测 child quiet |
| cleanup drift | 复制原 helper 函数 metadata、隔离 builtins 并逐次核 packet；effect 前检查清理能力；probe 失败仍 abort/recheck，区分 carrier/secondary |
| reentry | replay 和 cleanup callback 吞掉递归异常，外层仍失败且不能重试 |
| physical returns | replay、quiet、identity、observation、output、G3 实际内存对象/原字节 pin 先保留；编码/比较/G2及G3候选或commit故障不丢事实 |
| registry/sticky | active row 在操作前及返回后精确核验；正常 failure 必须匹配原 terminal row/fingerprint；foreign row 保留，emergency 明确记录未发布状态 |
| fixed windows | 阶段持有固定窗口入口；类 init/getattribute/setattr/switch/launch 替换不抢先执行，runner/closure globals 漂移拒绝；乱序 sticky |

资源终态分为 `_runtime_closed` 与 `_child_terminal`，两者均成立才可 `_closed=true`。失败强持 session 与已返回对象；只有成功完成才释放 binding/held/child/大结果引用。这些是**合成进程内机制断言**，不证明真实 Native 持久化、原 P1 重建、来源角色认证或全链物理 I/O。

原源仍保留六处首部 `FullRoleUnavailable` 及 public `bind_full_role`；`current()` 的 external_root/live_effect/actual_entry/audit_hook/launcher_quiet 均 false，activation_requires_source_successor=true。测试私有副本逐项删除六处 Raise、禁用副本 `current()`，独立登记 original source/clone/fixture pin；target fixture 无 import、builtins 为空，只处理内存数据。每 fixture 一个内存 child 对象，**0 个 fixture/project child 进程**；本包唯一实际子进程为 ordinary unittest runner。没有真实项目 Native owner、Source49 target、P1 内容读取、角色、模型或 solver 调用。

真实 entry/argv/channel 认证、外部 full context/anchor、Native 清理 class/helper/transitive graph 等价、audit hook、source-specific launcher/quiet、Guard2/Permission2 和 exact profile/graph **仍 OPEN**。所有 run/resource/science/formal/actual_F/production_seal/saved_P1 adopted gates 继续 false。完整 F 双侧独立21点/五小时/130CAS、19metrics、两层quiet、17targets、四份128KiB预留、180s原绝对时钟与12500/6500原帽不变；条件复用12159/12053尚未证明，整链资源准入未完成。

## 原失败与独立 successor

原 [role v1 root](../../results/tables/staged_rts24_saved_fresh_full_context_role_v1_non_authoritative/checkpoint.json)冻结保留：5文件/**844982B**。最后一项登记前复核意见在register完成后到达，指出 test01 漏传keyword-only `outer_deadline`。该包唯一26方法运行得到25正常、1 error；rc1/capture_error=null，全部54帧、stdout6362B、stderr3733B保留，无截断/kill/reader/cleanup，handle/pipes/readers终态。其费用 **11.672237799997674s** 不退款，CP accepted/accounting_complete=true、diagnostic_accepted=false。

v1 CP **8880B / SHA 76173a1df7041048f4d9cc0bee39fe90d0dea472335a57fd2e1808672995f401**。原 runtime/test/design/scope/driver 和登记/失败结果不修改。原 WIP source 另存 `before_repair.py`，**48360B / cdfbad787960572c520955bfa8e1187027a2d83d70cf5308050b965ec20ab838**，driver 固定原 pin，只读/编译不执行。

runtime v2 与已登记 runtime v1 逐字节相同：**54820B / 797ed4432e9422b73e5657c9725857b132e2877d69fa402d96c39fe4619ad181**。test v2 只修 test01 调用并指向独立 v2 source。v2 完整继承 v1 失败与费用，使用独立40秒预算。

## 最终验证证据

v2唯一26方法 **26/26、0 failure/error/skip**，runner **3.733s**，受控unit阶段 **9.962304200002109/12s**。原54个canonical帧逐nodeid配对，stdout6361B、stderr3148B，rc0/capture_error=null；无截断/kill/reader/cleanup，HANDLE/pipes/readers终态。439次健康memory samples：parent/child peak working set为34091008/46641152B，pair peak和最大80732160B、private和最大58695680B；未超帽。连续上界、combined retention、资源准入仍false。

独立只读 `sol_reviewer` 复核 exact own7、1441 inputs、276 archive、原失败继承、54帧与26报告、capture资源终态，**must_fix_open=[]**；只作PRE_SEAL。原findings保存于 [pre_seal.exit.json](../../results/tables/staged_rts24_saved_fresh_full_context_role_v2_non_authoritative/pre_seal.exit.json)。随后 saved canonical raw replay 与 checkpoint 均accepted。

registration **753165B / b5118e10c544a2118848d6a934bf5fe0d28215515b5347adb17e8b13f507a87d**；unit.exit **15272B / 062882eccb5f8064186abecb75ad47cc542ebc921606396286838495928f6a41**。

## 唯一最新账源与完整继承

[v2 checkpoint](../../results/tables/staged_rts24_saved_fresh_full_context_role_v2_non_authoritative/checkpoint.json)：**9378B / a534521c8f8365d82cfe395d85b280a78809a3129cc760f661247f8e852a2f29**，accepted/accounting_complete/diagnostic_accepted=true；acceptance_scope=`synthetic_full_role_failure_windows_only`。v2 root **6文件/803372B**。

| 阶段 | 本包费用/s |
|---|---:|
| register | 1.8925769000015862 |
| unittest | 9.962304200002109 |
| PRE_SEAL | 2.203939099999843 |
| saved | 2.1559218000002147 |
| checkpoint | 1.1741676999990887 |
| 合计 | **17.38890970000284/40** |

static **7.426605500000733/25s**，unittest **9.962304200002109/15s**。阶段5/12/5/5/5、child10、capture128KiB/32KiB、process256MiB/pair512MiB、root10文件/4MiB、record1MiB/checkpoint预留1MiB/1slot全部保持；余量不退款、不转包。

累计 **static653.3531790000227、pytest366.48897970000326、unittest350.93306609996944，总1370.7752247999954秒**。**53条不接受记录全部保留**，v2无新增拒绝。此次两包总新增费用29.061147500000516秒。

v2继承1436＋own7−Capture1/DRAIN1重叠2＝**1441 inputs /77046302B**；archive **276文件/31872995B**。最终独立逐文件输入/归档比较 **1717次/1529唯一路径，缺失0、pin mismatch0**；原39项dirty快照全部匹配。

下一包必须先继承本包1441＋root6−driver overlap1＝**1446 inputs /77829108B**；archive **282文件/32676367B**，再与实际新own精确union。不得预设下一own总数；完整核旧失败/charged/known pins。原成本模型root仍为6文件/835940B，其CP `0ece179a...`不变；它与本次role v1失败root是不同目录。

Source49 epoch **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**；NFC12原16文件及CP SHA **bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de**、B1–B3/原P2七输入和全部历史失败冻结工件保持。

## 接续顺序与工作区

下一步先把真实 approved source/entry/argv/channel、Guard2/Permission2、同一LIVE owner与actual launcher/quiet以及Native清理依赖图接入版本化successor。继续按原完整F DAG处理P1/source预算缺口、同owner同窗口实际读复用和昂贵失败/收尾费用；不能用本次宏操作计数或普通测试数代替真实物理读取和整链性能审查。实际Native/P1/Source49诊断及完整F须先准备具体包、次数、预算和停止条件，再取得专项运行授权。NFC12继续复用既有证据。

原39项并行工作区字节不动，尤其四个旧导航文件保留既有dirty。此次scoped Git只包括runtime v1修补、独立v2、两版tests/design/scope、两个result root及本交接。发布前HEAD为`69d4f746bec3fb2d9a203355ba65dc62617fb5b4`；实际发布提交用 `git log -1 --format=%H -- docs/plan/continuation_handoff_20261029_saved_fresh_full_context_role_v2.md` 查询。提交/push后核远端hash、index为空，并确认worktree仅剩原39项dirty；本交接不将宽goal设为paused。
