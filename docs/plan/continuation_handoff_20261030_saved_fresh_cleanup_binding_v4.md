# F：固定 cleanup anchor 与同 owner role 清理接线交接

2026-10-30，DRAFT_NONAUTHORITATIVE。用户恢复推进F；原八组full-context role修补已在[role v2交接](continuation_handoff_20261029_saved_fresh_full_context_role_v2.md)完成26/26机制验证。本检查点继续关闭Core晚绑定的清理窗口，并接通same-owner Core→role cleanup。root唯一writer，独立只读PRE_SEAL，无official verdict/receipt/production seal。持续推进goal保持active，新增模拟跨度0h，NFC12未重跑，完整F仍OPEN。

## 当前实现与验证

使用[Core50](../../experiments/staged_rts24_saved_fresh_pre_entry_lease_v50.py)、[role runtime v6](../../experiments/staged_rts24_saved_fresh_full_context_role_runtime_v6.py)、[设计v4](staged_deliverability_c_saved_fresh_cleanup_binding_design_v4.md)和[scope v4](staged_deliverability_c_saved_fresh_cleanup_binding_scope_v4.md)。三份测试分别为[Core](../../tests/test_staged_rts24_saved_fresh_source_cleanup_v6.py)、[role](../../tests/test_staged_rts24_saved_fresh_full_context_role_runtime_v6.py)、[关联](../../tests/test_staged_rts24_saved_fresh_cleanup_binding_v4.py)。

- Core50：98453B / `ea92529f8bf2792367bc961d3464309dd2892afc53ba0ada1f9833c41f49ca20`，与本轮冻结Core47–49逐字节相同。anchor在ownership交接前固定；ARMED→SPEC→OBJECT记录含完整资源、proof、原state/type/slot及前序身份。先append后写mirror，OBJECT先于claim/hook effect，runtime seal中anchor身份不再随晚绑定变化。
- role v6：63584B / `4655f822357d9c7a22957a73d18508ee939848721e46fceedc3bdd7e55d45156`。CoreOwnerCleanup capsule强持原owner/raw/namespace/anchor/CodeType/defaults/carrier。bind与entry核LIVE/RUNNING、未开始cleanup、无failure、完整OBJECT、原root image和IDLE账本；entry先核cleanup再调用clock。失败后仍从原held packet清理。
- namespace/B_S、Native及child终态分开。packet/mirror漂移不压住原anchor的Native finally；若journal丢失已提交OBJECT，不能声称对应B_S hook退休，即使Native已关闭也保留unresolved。任意协调篡改、跨线程、完整check/use与真实Native等价仍未证明。

唯一69方法 **69/69，0 failure/error/skip**：Core32、role26、关联11。48个expression-before/call-after场景覆盖SPEC/OBJECT/append的两代及每项mirror/seal/claim；registration保存23个实际call sites的source span、CALL offset与两侧marker。after-claim另有独立计数，before/after实际状态有断言，不再假定CALL opcode必产生trace事件。五项递归LOAD_GLOBAL静态集合固定：close/runner/image/journal为空，check_bindings只需dict/type。

这是精确Core/role cleanup orchestration与显式synthetic kernel、entry/bookend、namespace/B_S lifecycle、role上下文/效果的关联验证。项目Native/P1/Source49 target、solver、project/fixture child均0。ordinary validation child实际1；Capture1/DRAIN1实际使用Native sampler和runner HANDLE收尾。role六个内部effect gate与public binding继续关闭，不能将此验证解释为真实role/完整F授权。

## 原始记录与独立审计

[registration](../../results/tables/staged_rts24_saved_fresh_cleanup_binding_v4_non_authoritative/registration.json)：832606B / `e70ab0e86238d0761cf5e7725a4a66e8581d395f7e9e08fd56b28a307ce5be61`。

[unittest](../../results/tables/staged_rts24_saved_fresh_cleanup_binding_v4_non_authoritative/unittest.exit.json)：40910B / `92c5538e7d76df5d6f5e6392e06ce99a54b0878906010a78105d32f42ab77e9a`。140 canonical frames与69个nodeid顺序一致，runner 10.931s；stdout19277B / `7523b9af430ec02fa731c73dbb40fe80c02588680cf4b679d555ee125f0df542`，stderr9459B / `18450dc2f9d85ae4562741fe981d0c64e7bb7dbe60e107f4ea5b236055f51a47`。rc0/capture_error=null，无kill、截断、reader/cleanup错误，HANDLE/pipes/readers终态。

1000次健康采样：parent/child peak WS分别84590592/90460160B，pair peak-WS和最大175050752B，private和最大109801472B；未越process256MiB/pair512MiB帽。terminal_query_performed=false属于原last_live_poll_only合同；continuous_bound、combined_retention、resource_admission仍false。

独立只读sol_reviewer完整核exact own13、input1509、archive304、原始流与失败链，must_fix_open=[]。findings保存在[PRE_SEAL](../../results/tables/staged_rts24_saved_fresh_cleanup_binding_v4_non_authoritative/pre_seal.exit.json)。另一只读审计实际做1813次pin比较、规范化唯一1597路径、重叠216、缺失0、bytes/SHA mismatch0。随后saved原流回读与checkpoint均accepted。

## 冻结失败与费用

本轮四个包独立登记，没有覆盖或重跑失败包：

| 包 | 实际结果 | root | 包费用/s | checkpoint SHA |
|---|---|---:|---:|---|
| cleanup_binding v1 | scope仍68/10、机器69/11；unit启动前拒绝，0测试、0 child launch attempt | 4/836586B | 6.061028600001009 | `fe33e8f2fd4ee6af039eac5d5116786fbcbbc6e1f4fd52058128a5aee242825c` |
| v2 | 69方法：1failure/5error；pin字典/元组不匹配、CALL2018 locator未命中 | 4/895843B | 20.527027299998736 | `b71b4825805a8d4ea5114881c8d238ae22db487e904a246b99104461ba81d4bb` |
| v3 | 69方法：5error；48场景通过，verifier clone缺dict/type | 4/909851B | 20.816078600000765 | `ed70e42a372535f2a71423d93217f743a0f9dd76bb5e1ebd9ca1137df687e804` |
| v4 | 69/69，完整saved与账本接受 | 6/914872B | 28.250883000000613 | `8374da17a1a759ac94f48f9ca55e1479d59476a4256aeb1f799e7840d8ff896f` |

v1 CP通用child观察字段null，原unit pre-launch记录明确0 tests/child_launch_attempted=false；不把null伪装成Native见证。v2/v3各140帧及原始stdout/stderr、错误、capture、费用均保留；历史source-cleanup v1失败与原role v1失败是不同root，也完整继承。

v4各阶段：register2.845982200000435，unit20.22711569999956，PRE_SEAL1.959237299997767，saved2.070529600001464，checkpoint1.1480182000013883秒。static **8.023767300001055/25**，unit **20.22711569999956/30**，总 **28.250883000000613/55**。阶段帽5/30/5/5/5、child25、stdout128KiB/stderr32KiB、root10/4MiB、record1MiB、checkpoint预留1MiB/1slot保持。

唯一最新账源为[v4 checkpoint](../../results/tables/staged_rts24_saved_fresh_cleanup_binding_v4_non_authoritative/checkpoint.json)：**11886B / `8374da17a1a759ac94f48f9ca55e1479d59476a4256aeb1f799e7840d8ff896f`**，accepted/accounting_complete/diagnostic_accepted=true，acceptance_scope=`stable_cleanup_binding_and_core_role_join_synthetic_domains_only`。

累计static **684.9277867000303**、pytest **366.48897970000326**、unittest **414.9035574999798**，总 **1466.3203239000134秒**；**57条不接受记录**保留。四包合计约75.655秒受控验证费用，没有退款；这些数字不是协作总墙钟，也不是完整F运行时长。

## 完整继承与合同勘误

当前input **1509/83374392B**、own13/302745B、archive **304/36985643B**。下一包先做input1509+root6-driver overlap1＝**1514/84266616B**，archive304+root6＝**310/37900515B**，之后与实际新own精确union。本交接不在当前input map，后续使用时须明确纳入。

NFC12原root仍16文件，16项pin匹配；CP21591B / `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`。Source49 epoch仍`acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`；B1–B3、原P2七输入、原WIP before_repair和全部已发布绑定字节保留。

[上轮source-cleanup交接](continuation_handoff_20261029_saved_fresh_source_cleanup_v2.md)误抄了完整F指标数、targets、时钟和一个P1算式。正确为 **19 metrics、17 targets、180秒**。两个P1条件算式分别为`2*5055+3*683=12159`与`2*5002+3*683=12053`；均未证明物理复用，也不是Source49计数。原源码与预算从未改变。当前registration的`original_F_contract`来自[restricted AST提取器](../../experiments/staged_rts24_saved_fresh_contract_snapshot_v1.py)，保存原来源SHA/行号/表达式及WIP条件推导；原误写历史保持不变。

## 下一步与现场

下一完整模块是FullRolePreEntryBinding：保留Core `-P -B -s -S -c`入口，broker预先固定full context、role、argv/channel、source epoch、deadline和parent一次性fresh reservation；IMPORTING、audit handoff之前绑定同owner不可序列化entry root与默认DENY Guard2，LIVE后claim既有对象。不能直接沿用旧`-B -s adoption_v1.py --saved-entry`身份，也不能在LIVE后将字符串/JSON升级为权限。Namespace4单次expectation consumer调用后关闭owner，须由后继改为跨reconstruct→launch/quiet→G3的角色生命周期。

随后将Guard2 revoke、child abort/terminal、channel/registry retirement按固定来源加入早期cleanup域，再接source-specific launcher/inner quiet与外层supervisor。原双侧独立21点、五小时、130CAS、19metrics、17targets、四件128KiB、180s绝对时钟、12500/6500帽继续保持；完整call DAG、物理读取合法复用、整体资源/性能和所有真实运行门禁仍OPEN。任何项目Native/P1/Source49诊断先准备具体包、次数、预算和停止条件并取得专项运行授权；普通验证不扩大权限。

原[42项并行snapshot](continuation_handoff_20261029_saved_fresh_source_cleanup_state_v1.json)的exists/bytes/SHA全部匹配，预先删除的project_abstracts.md仍按exists=false处理；引言、摘要、图件、旧导航与blocker/execution-plan dirty内容未改。进程核查仅见VSCode Jedi，没有项目验证/solver/Native运行。

本轮开始HEAD为`b7aaf2235375a7c354f63646c9deab301a58cc74`。scoped Git纳入四代Core/role/测试/设计/scope、四个result root、合同提取器与本交接，保留原42项并行状态。发布核所有Git blob与本地原字节、远端hash及空index；实际提交可用`git log -1 --format=%H -- docs/plan/continuation_handoff_20261030_saved_fresh_cleanup_binding_v4.md`查询。持续推进goal不因本检查点变为paused或complete。
