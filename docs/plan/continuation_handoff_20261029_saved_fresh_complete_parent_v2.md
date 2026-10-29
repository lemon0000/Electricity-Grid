# F：source-held Parent40、profile 关系与失败封存检查点

2026-10-29，DRAFT_NONAUTHORITATIVE。承接 [bootstrap actor v3](continuation_handoff_20261029_saved_fresh_bootstrap_actor_v3.md)。宽 goal“持续推进”保持 active，完整 F 未完成。本轮实现 post-spawn Parent40、complete validator1 与 QuietActor2，并完成 23 项普通验证、独立只读 R3 PRE_SEAL、saved 原流重开和 checkpoint。root 唯一 writer，retained_lifecycle_review 的 must_fix_open=[]；没有 official verdict、receipt 或 production seal。项目 Native owner、Source49 目标执行、P1 内容读取、角色、模型、solver 均 0，NFC12 未重跑，新增模拟跨度 0h。

## 当前实现

- [Parent40](../../experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v40.py)是另获授权 outer 创建 child 后的 post-spawn owner，当前没有 launcher 或 P1 reader。source_dispatch 要求 outer 独立绑定实际 source raw 与 expected pin，返回 held capture/run/observation spec；public convenience methods 不作为可信入口。实际 raw 固存在 namespace，程序 witness 核 namespace、function/class、constants、完整 native builtins、direct attributes、private module copies/functions 及 Path/Popen/Thread/io owner methods。held 闭集为 immutable tuple，entry 在隔离原 CodeTypes 中核 image，恢复从 immutable expected rows 重建 module copies。
- 唯一 quiet actor 执行 capture → 固定 release → drain → close HANDLE → finish。Parent 本身持有原 manifest/transport/argv、实际 direct child、原 stdout/stderr 和前后 input context，不接受独立 caller quiet/raw/source-map 作为事实根。source program 或原/私有 module roots 漂移会拒绝；恢复路径不执行 caller replacement。
- [complete validator1](../../experiments/staged_rts24_saved_fresh_complete_bootstrap_validation_v1.py)的 replay_retained 核 exact actor type、creating parent、registry row 和 held finish，再核 manifest SHA/transport/argv/release/原始流、child kernel identity、writer/pipes/readers/HANDLE，以及同一 parent/child 的 live memory guard。saved audit 使用原 receipt parent PID。producer_result 只能从该 child 单一 canonical report 派生；其 terminal/permission 必须与 bootstrap actor、顶层 permission、namespace/consumer/close_calls/pending 一致，然后复用原 replay2/packet2 的 source、683-map、G0/G2/G3、raw pins 与可逆数据检查。
- startup/import profile 的完整原流关系分别递归到更早 discovery/import-discovery 的 accepted parent receipt、profile、manifest、admission、registration；scope/env/helper/source/transport/pin 及独立旧进程关系受检。当前 observed profile 必须 exact。可信 external registration anchor 固定 None，两个非 startup exact graph contract 固定 None；自洽文件、profile 或 256 graph stop cap 均不能使它们变成 accepted。真实 profile artifact/anchor 仍未产生。
- [QuietActor2](../../experiments/staged_rts24_saved_fresh_parent_quiet_actor_v2.py)在 terminal snapshot/result canonical bytes 固化后，删除 exact registry row并清大引用。失败 drain、writer、handle 或 reader 未闭合则保持 UNRESOLVED；foreign row 不删除。retire 后再抛错可从实际 RETIRED state 重开原 retirement evidence，避免重复物理关闭。Parent 的 capture/row/candidate JSON、cap、retire 前后和 registry fault 都保存原 primary、递归 cause/group/secondary、原流和固定 rejected schema；handler 自身失败进入可重开的 emergency UNRESOLVED schema，并保留 owner/primary/引用。

Core44/Probe42/Loader5/Namespace4、Permission1/LC6/Helper7/Coordinator2、packet2/replay2 均保持冻结原字节。Permission1 的 public issue/verify/claim 继续永久拒绝；Parent40 当前也没有构建真实授权的来源。Source49 原 _SavedLaunchIssuer 已关闭，不能复活为本诊断许可。真实 outer pre-spawn reservation、准确 child/argv/manifest/transport/source/deadline/nonce 消费、认证 release、child self bookend，以及 parent 独立 P1 读取 grant 仍须后继设计和具体授权。

## 失败与通过证据

[scope v1](staged_deliverability_c_saved_fresh_complete_parent_scope_v1.md)唯一 23 项全部执行，22 pass/1 failure/0 error/skip，runner **4.992s**、outer **8.910682099987753/12s**；48 canonical 帧包含完整拒绝 report。rc=1、capture_error=null，stdout 8507B、stderr 7525B，无 kill/truncation/reader/cleanup，handle/pipes/readers 均终态。唯一失败是 test10 的 child_pid 变异先破坏 DRAIN2 内部 child_pid==drained_child_pid，触发 AssertionError，未到预期 Parent ValueError；不是漏放错误 PID。source/test/scope/driver/raw 全部冻结，未原路径重试。

v1 register **1.0888222999928985s**、unit 拒绝 **8.910682099987753s**、checkpoint **0.5203438000171445s**，总 **10.519848199997796/40s**。root 4 文件 **783948B**；CP **7627B**，SHA **d194849e7eca6ce4ddaa0c581e3d47dfdba35e2354f5d5b05ea3b327fc4c1a30**。accepted/accounting_complete=true 仅保全账，diagnostic_accepted=false；累计 **1320.1139979999673s**、**52 条拒绝**。

[scope v2](staged_deliverability_c_saved_fresh_complete_parent_scope_v2.md)只修改 [test2](../../tests/test_staged_rts24_saved_fresh_complete_parent_v2.py) 的 test10：选择与原 parent/child 都不同的正 uint32，同步 child guard 的 binding 和 drained_child_pid，使 guard 内部自洽；原 quiet kernel/direct-child PID 不改，重算 observation pin，进一步要求 Parent 的 same live sampled parent/child pair ValueError。独立复核确认没有放宽生产检查；三份生产源码与 v1 registration 的 pins 完全相同。

v2 实际 **23/23，0 failure/error/skip**，runner **4.195s**、outer **6.867313900002046/12s**；48 canonical 帧含完整 accepted report。rc=0、capture_error=null，stdout **8506B**、stderr **4454B**；无 kill/truncation/reader/cleanup，handle、pipes、readers 均终态。包括：原流/manifest/transport/argv/release、actor/probe/packet/namespace/permission、live memory pair、默认 graph/anchor 拒绝、profile 工件及旧进程、source factory、原/私有 module/class漂移、capture 失败、row/candidate JSON与cap、retire前后抛错、foreign registry、原 primary/cause、handler自身失败与 rejected/emergency 重开。

每包两个固定 stdlib tiny children，均通过 source_dispatch 返回 spec 的 capture/run/observation 完整调用；只读 system temp 合成 payload、固定 stdin release、sleep 0.12s、查询自身 PID/creation/command，再输出合成 probe/trace。private source copy 明确替换 context、synthetic exact graph/anchor 以覆盖机制分支；startup 递归另有纯数据 fixture。这些成功不证明实际项目 import/profile/permission/graph。两包合计四个 ordinary children，项目 Native/P1/Source49 目标仍 0；旧 export 70 项与 NFC12 都未重跑。

v2 为 373 个健康 native memory samples：parent peak working set **33206272B**、child **84299776B**、两者 peak 和最大 **117506048B**、private 和最大 **94601216B**。这些只覆盖取样观测，不证明 toy descendants 或完整 F 的连续/组合内存界；continuous_bound_verified、combined_retention_verified、resource_admission 均 false。

## 当前账源与冻结输入

v2 root：`results/tables/staged_rts24_saved_fresh_complete_parent_v2_non_authoritative`，6 文件 **786045B**；CP **8259B**，SHA **a66f0f68239fe1d1b46d69e523527cdfd5f489e826eab5163ebe681baa9f56e0**。accepted/accounting_complete/diagnostic_accepted 均 true，acceptance_scope=retained_parent_binding_profile_and_failure_units_only。

阶段各一次：register **0.5265462000097614s**、unit **6.867313900002046s**、pre_seal **1.417010000004666s**、saved **1.0181942000053823s**、checkpoint **0.5231626000022516s**。本包 **10.352226900024107/40s**，static **3.484913000022061s**。5/12/5/5/5 秒、child 10s、static 25/unit 15/总 40s、ordinary capture 128KiB/32KiB、256MiB/process/512MiB pair、root 10 文件/4MiB、record 1MiB/checkpoint reserve 1MiB 全部保持。

下一账源固定该 CP：累计 static **636.4975629000212s**、pytest **366.48897970000326s**、unittest **327.47968229996695s**，总 **1330.4662248999914s**，**52 条不接受记录**。两包总 **20.872075100021903s**；旧费用不退款，剩余不转用。当前 input **1408/74309474B**、archive **259/29406028B**、own 5。后继精确继承 expanded 1408 加 root 6 扣 driver overlap 1，即 **1413 inputs**；archive **265/30192073B**，新 own 须显式 union 并核完整历史失败，不能只核 Source49/NFC12 子集。

关键 source pins：Parent40 **43645B / bd049afa324250213d0496a2c4ab0fb4c4c408676507955e6c117a80332f1d2b**；QuietActor2 **22359B / c6c647b5a9237a63ded591e24674755e3b141343594ae234360d23f22b82fa3b**；validator1 **73927B / 762224af9656c5dfaa75fa4594bf9d14aea1c1bf37af637aabfb1ad79879f33a**。registration **733501B / f0189208b69058f2242938e452e47b7b28291e0bb1b7b024420e563b58373462**；unit **19701B / 6b344be8904247bdcc30c88186fcc005b74b3eff781fd697aba6ca9a891bb560**。全部登记后字节冻结。

最终两包 **3364 次 pin 比较/1500 个唯一文件，bad=0**；独立 PRE_SEAL 核 1408 inputs、259 archive、5 own 全一致。原 39 项并行 worktree SHA 保持。Source49 epoch **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**、NFC12 全 16 文件及 CP **bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de**、B1–B3、原 P2 七输入和全部旧失败工件保持。Native 候选 root v2 未创建；现场只见 Jedi35552 和核验进程，无 formal/native/solver 活动。

## 下一步

1. **先固定完整 DAG、真实调用倍数与 whole-workflow 预算。** 纳入 outer reservation/spawn、startup/discovery/admission、import/profile anchor、LIVE producer/P1窗口、packet capture/restore、单帧输出、Parent quiet、递归 saved/profile 重开、独立 683 内容读取、publication/failure/retirement。先消除可证明安全的重复 I/O、解析和证据重放。原 construction 43、producer 107 静态基线、graph 256 stop 或普通 unit 耗时均不能当作完整新链准入。
2. **准备真实授权后继及 exact graph/profile 可信锚。** 为 Permission/LC/Helper/Coordinator/replay/outer 增加固定 source/scope 的真正 grant 创建点和 child 全绑定消费，独立定义 Parent P1 grant。当前 Parent40 只接 post-spawn 已创建 child；它不承担外层 pre-spawn 权限。当前 None gate 必须保留到其对应冻结证据闭合，不能把 synthetic contract/自洽 admission 填成真实根。
3. **具体运行前再适用 agent.md 第 9 节和专项授权。** 真实 Native/P1、代表性 packet/graph/profile 和昂贵失败成本仍未实测；whole-workflow wall/RAM/storage 未准入。保留所有现有通过/失败证据，不重跑旧 70 项或 NFC12。当前可继续 source/DAG/授权设计及已授权普通验证，不能据本检查点启动真实项目 child 或长链。

本检查点 scoped Git 包含两个 scope 的失败与通过记录、全部新源码/测试和本交接。四个共享导航仅 index 发布“新前置段 + 原 HEAD 正文”，原 39 项 worktree 字节不改；remote/index/39 项终态以发布后现场读回为准。role/permit/science/resource/formal/run/F gates 均 false，宽 goal 保持 active。
