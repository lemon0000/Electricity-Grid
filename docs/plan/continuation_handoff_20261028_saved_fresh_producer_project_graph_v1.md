# F：跨项目闭包连续性组件已验证，retained producer继续开发

2026-10-28，DRAFT_NONAUTHORITATIVE。宽goal“持续推进”保持active；完整F未完成。承接[代码桥v3检查点](continuation_handoff_20261028_saved_fresh_full_producer_bridge_completion_v3.md)。root唯一writer，bridge_pre_seal独立只读PRE_SEAL和终态重开；没有official verdict、receipt、production seal或新运行权限。

## 本轮已实现与实际证据

已实现[project graph组件](../../experiments/staged_rts24_saved_fresh_producer_project_graph_v1.py)、[12项synthetic测试](../../tests/test_staged_rts24_saved_fresh_producer_project_graph_v1.py)、[controller](../../results/tables/staged_rts24_saved_fresh_producer_project_graph_v1_non_authoritative/driver.py)，合同为[graph scope](staged_deliverability_c_saved_fresh_producer_project_graph_scope_v1.md)。组件解决旧namespace graph将跨project函数/module降为external identity的缺口，递归保留function/code/defaults/kwdefaults/annotations/dict/closure、class/dataclass/descriptor、container aliases/cycles、完整ModuleSpec和支持loader state，并观察静态global/attribute目标及实际builtin fallback。未支持值、foreign project globals、未知loader和危险mappingproxy拒绝，避免执行被观察代码或未知mapping方法。

独立fixture AST oracle精确核project module/function/class、global/builtin/default edges及实际target identity，另核导入Box/func alias原对象。ModuleSpec/loader_state/loader额外state、conditional external callable替换、NotImplemented owner、metadata SimpleNamespace、builtin字典置换等反例通过。snapshot强持对象并核creator/seal和结构/identity，不能复制或序列化；source map仍是调用方提供的字节，不自行变成初始认证。

**12/12、26 canonical帧、0 failure/error/skip**；runner0.608s，外层unit **7.838075199993909/10s**，childrc0、capture_error=null。stdout4250B、stderr2146B及pins均匹配；HANDLE、pipes、reader threads终态，无kill/truncation/cleanup/reader错误。native sampler267 healthy samples，peak parent46850048B、child54091776B，同次peak字段和最大100941824B，未触发停止帽；不证明continuous、descendants、128MiB retention或实际37-module资源准入。

Root `results/tables/staged_rts24_saved_fresh_producer_project_graph_v1_non_authoritative`，**6文件653581B**。checkpoint **9227B/SHA 7fd488b14a7c1e4a8171bebb37b81944a9c95f026116f16e2a79c5fee344a6b2**，accepted=true、diagnostic_accepted=true、accounting_complete=true，范围严格为`project_object_continuity_observation_only`。register/unit/PRE_SEAL/saved/checkpoint全部accepted，accounting_errors=[]、pin_errors=[]。所有执行source/scope/input/result bytes冻结，不在原路径改或重跑。

独立重开逐文件核**1209 inputs / 57459817B**、own7、**168 archive / 15673460B**及路径唯一，无mismatch；Source49 49 pins及epoch不变。saved unit pin/report与graph contract canonical pin逐字匹配，103处graph/record gate字段全部false。12 known pins和4 charged pins无漂移。这里只验证continuity组件，不证明实际Source49初始正确性或真实producer调用。

|阶段|charge秒|cap秒|
|---|---:|---:|
|register|2.666062000003876|5|
|唯一12-node unit|7.838075199993909|10|
|PRE_SEAL|3.5318536999984644|5|
|saved|3.126390100005665|5|
|checkpoint|1.5600810000032652|5|

本包static **10.88438680001127/25s**、unit **7.838075199993909/15s**，总 **18.72246200000518/40s**。累计static **558.324625700024s**、pytest **366.48897970000326s**、unittest **219.61528909999834s**，总 **1144.4288945000255s**；不接受仍 **41条record**。没有新增受控失败，v1编译上下文拒绝与v2 unit外层超帽及所有旧失败/预算完整保留，未用余量不退款、不重置、不转用。上述是capture阶段费用，不是编辑/审查/Git全部wall。新增模拟跨度0h，真实P1读取/Source49目标模块执行/真实owner producer调用均0。

## 完整目标与接下来必须继续的工作

[retained producer整体合同](staged_deliverability_c_saved_fresh_retained_producer_lifecycle_scope_v1.md)仍是**未登记开发草稿**，本轮没有实现或测试其生命周期。目标仍是同一个真实LIVE owner中的：

`expectation53 → context/check_context → adapter.hold(source, expectation.image) → exact HeldInput/raw/caller-image → G2 → G3 → cleanup → parent quiet后reopen replay`。

下一步按整体合同写固定producer helper和bootstrap接线，不能以本组件通过缩小完整F目标：

1. 必须排他占用原消费槽位。保持exact owner、owner._consumer_plan、原plan[8] binding、plan[4] adapter和原ENTRY globals；PREPARED提交时按原Core39 runtime_seal语义将owner consume-state置RUNNING并重封，阻止第二consumer。若不复用slot，写独立Core successor的producer lease。不要用会立即close的consume_once，也不调用会重新_prepare binding的_probe接口。
2. 从冻结v3派生代码及report pin核同一CodeType，以FunctionType配原ENTRY globals构造私有函数，不写回ENTRY globals。真正capture/context/hold在单独准入包内执行；原context即使输出是pytest tmp也会读source/EXE/INHERITED/P1 anchor，普通synthetic测试不可直接调用真实ENTRY globals路径。
3. **独立初始oracle仍OPEN。** 当前snapshot始终initial_project_state_authenticated=false，不能通过自观察发放producer/runtime许可。需独立source/module/class/default/dataclass oracle，并固定actual registry is sys.modules、完整37-module/alias/origin集合与外部conditional TCB直接边。旧NF9 profile元数据核到37 project modules与Source49 runtime set相符，无额外project file；尚未在实际对象集合上运行本graph。未知值必须fail closed，不能把旧10-binding/7 edges当完整closure。
4. 旧图cap40不能绕过。新增跨module图及retained state的真实调用量、模块/节点/编码、RAM/retention/全workflow wall与cleanup预算须完整核定，再进入新helper/native后继。当前8MiB编码帽不是retained-memory证明；大bytes只pin编码但强持原对象，实际总体RAM仍须独立准入。
5. 生命周期固定PREPARED→RUNNING→HELD→G2→G3→CLOSED；同一expectation/context/HeldInput/binding/runtime强持至最终bookends。全量hold一次，G2/G3各原full bookend一次；完整raw keyset/pins、external expectation image、adapter.caller_image精确相等。成功G3后owner CONSUMED再唯一close；失败owner FAILED，保存primary与各secondary原对象且sticky，任何bookend/cleanup/terminal不确定为UNRESOLVED。成功close释放live capability，只返回有界数据；不能从JSON重建或跨进程转移能力。
6. 普通测试用独立synthetic globals执行AST-extracted代码、拒绝型真实P1 reader和纯transition-table oracle；再覆盖每个partial stage、同一HeldInput identity、capture/context/hold/G2/G3/final/close fault及source/global/default/code/module替换。现有graph的12项不能替代这些lifecycle/真实owner测试。

P1/actual role/native校准/模型/solver/长实验仍遵守各自明确授权和agent.md §7–9；先完成可审实现及整体路径准入。producer、full runtime/P1、issuer/role/permit/OwnedChild/Job/独立TCB、父端科学采用、资源、正式、run/F权限仍false或OPEN。

## 保全、现场与同步

NFC12及Source49原样保留，不重跑NFC11/NFC12、代码桥v1/v2/v3或本graph包，不恢复旧PID。39项并行论文/插图/文献工作区bytes保持原样；四共享导航仅在Git index发布本轮prefix+原HEAD正文，避免纳入并行dirty。最终以remote读回hash、index为空、本轮scope clean且原39项dirty哈希一致为准；不称全局worktree clean。当前无研究任务运行，仅VS Code Jedi。下一次继续先核本交接、整体retained合同、Git/进程和真实字节，再实现第1/2/5项，初始oracle和资源门槛并行保留为明确开放项。
