# F：pre-LIVE bootstrap actor 与 Parent quiet 普通验证检查点

2026-10-29，DRAFT_NONAUTHORITATIVE。承接[producer export v2](continuation_handoff_20261029_saved_fresh_producer_export_v2.md)。宽 goal“持续推进”保持 active，完整 F 未完成。本轮完成版本化接线草稿、pre-LIVE 失败清理和 retained Parent quiet actor 的普通验证；真实 Source49 目标模块、P1 内容、项目 Native owner、角色、模型和 solver 执行均为 0，NFC12 未重跑，新增模拟跨度 0h。root 唯一 writer；retained_lifecycle_review 完成独立只读 R3 PRE_SEAL，must_fix_open=[]，未形成 official verdict、receipt 或 production seal。

## 当前源码与边界

- [BootstrapActor2](../../experiments/staged_rts24_saved_fresh_bootstrap_actor_v2.py)在 ADOPTED 创建点保存同一原 owner、Core close、独立 permission revoke 和 Coordinator2 program，把 guard install、import 返回、IMPORTING prepare_consumer、finish_import 到 LIVE/PREPARED、完整 coordinator run 和 terminal 纳入同一 actor。状态与方法 CodeType/default/global 快照绑定，调用时从原 program 重建函数；公开 convenience/coordinator 名称替换不改变 held 原调用。import_discovery 只进入 OBSERVED 并关闭，不创建 consumer。producer 提前 close(None) 进入失败终态。
- prepare_consumer 自身已清理的失败不重复关闭；其他 pre-LIVE 错误先独立 revoke/retire 再使用 held 原 close，保留原 primary、secondary 和失败引用。terminal/permission image 使用 raw byte pins；commit 在写任何 slot 前形成完整 candidate image/seal。再次 seal/cleanup 失败仍保留 FAILED、原 primary、secondary 和可形成的 fallback seal。成功 terminal observation 为 canonical JSON 深副本，嵌套返回值改动不污染内部状态。
- [变换 v2](../../experiments/staged_rts24_saved_fresh_bootstrap_actor_transform_v2.py)派生 [Loader5](../../experiments/staged_rts24_saved_fresh_project_bootstrap_loader_v5.py)、[Core44](../../experiments/staged_rts24_saved_fresh_pre_entry_lease_v44.py)和 [Probe42](../../tests/staged_rts24_saved_fresh_runtime_handoff_probe_v42.py)，复用已冻结的 [Namespace4](../../experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v4.py)与 [DRAIN2](../../experiments/staged_rts24_saved_fresh_memory_drain_v2.py)。Core42/44 runtime class CodeType 完整一致。候选 manifest schema 为 complete_bootstrap_manifest_v1，三 case 为 discovery/import_discovery/producer；producer 指向新 Native root v2 的 import_profile.json 并要求 startup profile。helper 闭集 11 项，包含 Coordinator2/Actor2。Loader 在 ADOPTED、admission=None、public permission DISABLED 时返回唯一 actor。
- [ParentQuietActor1](../../experiments/staged_rts24_saved_fresh_parent_quiet_actor_v1.py)持有实际 Popen、原 stdin、固定 release writer、已核 raw DRAIN2、私有 drain observation、原 kernel identity 与 handle。它自己创建 writer、drain 和 close handle，禁止 caller drain closure 或 caller writer 充当事实来源；writer 错误、raw/pid/pipe/reader/handle 证据在返回纯数据前固化，caller 改副本不改变原事实。physical quiet 与 child/transport success 分开，干净非零 rc 可物理 quiet；该 actor 不发放 P1 读取权。真实 Parent40 和 complete validator 尚未实现。

以上接线仍使用固定 Permission1、LC6、Helper7、Coordinator2；public issue/verify/claim 始终拒绝。普通夹具中的 private positive permission 不等于真实外层授权。真实成功路线需要版本化 Permission/LC/Helper/Coordinator/parent replay 后继及独立授权设计，不能将 profile、False gates、release 字节、kernel identity 或 quiet 数据当作 P1 权限。

Native 候选目录 v1/v2 均未创建或执行。固定 release 格式 SAVED_PRE_ENTRY_V1:<manifest sha>\n 仍只是数据。后续真实 outer 必须在 spawn 前预约 grant，绑定准确 child identity/argv/manifest/transport/source/deadline/nonce，完成消费、认证 release 与 child self bookend；parent 独立 P1 读取还需单独授权。Source49 原 _SavedLaunchIssuer 已关闭，不能复活为本诊断许可。accepted independent import profile artifact 及其与实际项目状态的关系仍 OPEN。

graph_call_stop=256、image 4MiB、未来 stdout 327681B/stderr 131072B 均仅为候选 stop caps。旧 construction 43 次和完整 producer 107 次静态基线不能当作新 whole-workflow 调用量、wall/RSS/storage 准入；observed_complete_calls 仍为空，whole_workflow_admitted=false。真实完整包尺寸、Parent 逐 SHA、昂贵失败路径及 combined retention 仍待代表证据。

## 失败记录与当前验证

[scope v1](staged_deliverability_c_saved_fresh_bootstrap_actor_scope_v1.md)登记后冻结全部输入，唯一 20 项 unit 为 7 pass/13 errors，42 个 canonical 帧包含拒绝 report。夹具 handcrafted globals 缺 __builtins__ 名称、make_plan 错依赖未执行 Native root 的 import_policy.json，未到达完整目标分支。register 1.1615617999923415s、unit 拒绝 3.8520079999871086s、checkpoint 0.5725689000100829s，共 **5.586138699989533/40s**。root 4 文件 794276B；CP 9655B，SHA **fb3b4cafd4083b3b064481b9d790dc7e9c6eb23d69213e38eb717164310a16dd**。accounting_complete/accepted=true，diagnostic_accepted=false，累计 1294.0876530999478s、50 条拒绝。

[scope v2](staged_deliverability_c_saved_fresh_bootstrap_actor_scope_v2.md)只修夹具 builtin snapshot 与纯 metadata manifest；dummy profile/policy pins 仅供本地夹具，不形成真实 import/launch 输入。唯一 unit 有 20 组 start/end、41 个 canonical 帧，无最终 report；stderr 32KiB 帽触发 kill/truncation 和 output_limit_or_reader_error，不能记为整包通过。它暴露 Actor1 的生产缺陷：terminal/permission canonical bytes 再嵌入 JSON image，TypeError 会遮蔽原 primary，并可能在 seal 失败后留下半发布字段。register 0.9969454999954905s、unit 拒绝 4.170200900000054s、checkpoint 0.5986667999823112s，共 **5.765813199977856/40s**。root 4 文件 796797B；CP 6360B，SHA **6be9dd0a13e09d326903b55ea153c01403bed055c72107419932400860624be0**。仅账务保全，累计 1299.8534662999257s、51 条拒绝。两次失败的 source/test/scope/controller/raw 记录与费用全部保留，没有原路径重试或改字节。

[scope v3](staged_deliverability_c_saved_fresh_bootstrap_actor_scope_v3.md)修正 Actor2 image、原子 commit、失败保全与返回值隔离；[唯一 23 项 unit](../../tests/test_staged_rts24_saved_fresh_bootstrap_actor_v3.py)保留原 20 项并增加三个相邻回归。实际 **23/23，0 failure/error/skip**，runner **2.817s**、outer **5.703505900019081/12s**，48 个 canonical 帧含最终 report；rc=0、capture_error=null，stdout 7897B、stderr 4068B，无 kill/truncation/reader/cleanup 错误，process handle、pipes、readers 均终态。

覆盖 ADOPTED/IMPORTING/prepare/finish/LIVE 的 private owner 顺序、原 close/revoke、source/guard/method drift、foreign thread、实际 Loader5 body 在 FakeRuntime 下的返回 actor、public issue 拒绝、runtime class CodeType、三 case manifest/helper/profile 路径、完整命令长度、Parent quiet 故障和封存返回值。两个固定微型 stdlib Popen 只读取 stdin EOF、sleep 0.12s、输出 release SHA 并 exit 0/3，child drain 1s、join 0.5s/wait 1s。它们验证真实 writer/drain/handle 路径，未执行项目 Native owner 或 P1。旧 export 70 项证据逐 pin 复用，未重跑。

286 个 native memory samples：parent peak working set 33832960B、child 128618496B、两者 peak 和最大 162451456B、private 和最大 185892864B。取样无 cap/error；这些观测不证明 toy descendants 或完整 F 的连续/组合内存界。continuous_bound_verified、combined_retention_verified、resource_admission 仍 false。

## 当前账源与完整继承

v3 root：`results/tables/staged_rts24_saved_fresh_bootstrap_actor_v3_non_authoritative`，6 文件 **777498B**。CP **10325B**，SHA **369a5b87a1c979d357e3dcad6fa952d019e4c61d1dfbdad7b976102cb0e467d4**；accepted/accounting_complete/diagnostic_accepted 均 true，acceptance_scope=pre_live_bootstrap_actor_and_retained_parent_quiet_units_only。

阶段各一次：register **0.9885771000117529s**、unit **5.703505900019081s**、pre_seal **1.209788700012723s**、saved **1.3289590000058524s**、checkpoint **0.5098527999944054s**。本包 **9.740683500043815/40s**，其中 static **4.037177600024734s**。5/12/5/5/5 秒阶段帽、child 10s、static 25/unit 15/总 40s、ordinary capture 128KiB/32KiB、256MiB/process/512MiB pair、root 10 文件/4MiB、record 1MiB/checkpoint reserve 1MiB 均保持。

下一账源固定该 CP：累计 static **631.4034837999891s**、pytest **366.48897970000326s**、unittest **311.70168629997715s**，总 **1309.5941497999695s**，拒绝 **51**。本轮三包合计 21.092635400011204s；原费保留，旧剩余不转用。v3 精确输入 **1391/72511331B**、archive **249/27844582B**、own 10。后继继承 expanded 1391 加 root 6 扣 driver overlap 1，即 **1396 inputs**；archive **255/28622080B**，新 own 须显式 union，核完整历史及失败记录。

registration 723077B/SHA **b7262c2262d5a140919fe8de44fbe07d67553853df566e1ee4974ad76c263f7b**；unit 18379B/SHA **8261ba0bccbd3a3659311de33c5552ba81dc7af75f08a6a85e361898835d9ae4**。Actor2 15114B/SHA **7d8b69f936b3ad71bb01a6c7318571f6bdb5459589f26f782bd2d3f9c586517c**；transform2 11026B/SHA **1d446fcf5f95a5777a9fe0776bb27702e4925e8b2e37471ea503756e16ffa964**；Loader5 4809B/SHA **acec252160024d46c1fb608df4c893421884cfe005b7a84878ac05c7b086329e**；Core44 69895B/SHA **43f0b2c9add534a4a4fb74413c29fe4649d9a696475a73e80572a7eef15603cc**；Probe42 32006B/SHA **1a71ac951f95d02dbc987bc5db39a449be69fa2b5fc7dc2393dc5a6c8b308c4d**。登记后上述字节冻结。

最终三包全量核对 **4955 次 pin 比较/1483 个唯一文件，bad=0**，包括输入、own、archive、known 和 charged records；原 39 项并行 worktree SHA 全部一致。Source49 epoch **acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875**、NFC12 全部 16 文件及 CP **bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de**、B1–B3、原 P2 七输入及全部历史/失败工件保持。process 快照仅 VS Code Jedi35552 和本次只读核验进程，无 formal/native/solver 活动。

## 下一步

1. 先实现版本化 Parent40 与 complete validator，把 held ParentQuietActor 的实际 direct-child identity、stdout raw pin、writer/drain/readers/pipes/handle terminal 接到完整 producer 数据重开；单纯 dict quiet observation 不足以授权或证明这些事实。同步 accepted independent import profile artifact 及其来源/状态/消费关系。
2. 设计固定 source/scope 的真实外层 grant 创建点、spawn 前预约和 child 全绑定消费，并为 parent 独立 683 文件内容 SHA 重开建立单独 grant。准备 Permission/LC/Helper/Coordinator/replay 所需后继，保持当前冻结 public DISABLED 记录；不能通过 callback、bool、manifest 或 profile 绕过发行边界。
3. 在实际执行前按 agent.md 第 9 节，先固定完整 DAG、phase/call counts、P1/packet/parent 的 wall/RAM/storage、失败清理成本及具体授权；新 Native/P1/完整长链均尚未准入。继续复用已保存通过证据，避免重跑 NFC12 和旧 70 项。

本检查点 scoped Git 发布包含新增后继、失败包与当前账源。四个共享导航只在 index 中发布“新前置段 + 原 HEAD 正文”，原 39 项并行 worktree 字节不改；远端 hash、index 和 39 项终态以发布后现场读回为准。role/permit/science/resource/formal/run/F gates 均 false。新对话从本交接、agent.md 第 7–9 节及最新 Git/process/pin 快照继续，宽 goal 保持 active。
