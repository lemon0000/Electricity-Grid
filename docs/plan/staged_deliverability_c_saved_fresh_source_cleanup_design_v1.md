# F：Core45 来源清理交接草稿

2026-10-29，DRAFT_NONAUTHORITATIVE。接续 [role v2 交接](continuation_handoff_20261029_saved_fresh_full_context_role_v2.md)，在 [Core45](../../experiments/staged_rts24_saved_fresh_pre_entry_lease_v45.py) 接入实际创建、交接与清理路径。原 Core44、role v1/v2、失败工件与 NFC12 保持。root 唯一 writer，独立只读 PRE_SEAL；执行范围见 [scope](staged_deliverability_c_saved_fresh_source_cleanup_scope_v1.md)。

## 实现与不变量

`_Resource.__init__` 在取得 HANDLE 前保存清理根、原 API 行、Python callable metadata 与审计账本身份。`open()` 从局部保存的两个实际返回值形成 immutable LIVE tuple；creating lease 将该 tuple 强持有于 `ownership[6]`，转交时只核对，不以当前 pending 与 opened 相互重新认证。`ownership[5]` 保留 construction roots。

runtime 的 cleanup packet 在 owner commitment 前创建；base roots image 与实际根对象、原 member descriptors、Native 数据和执行 ledger 由 owner 的 immutable anchor 独立保存，其身份进入 runtime seal。packet 提供镜像状态。唯一 `resource.owner = target` 写就是清理权限的交接点。交接前原 owner 继续使用原收尾；交接后即使 audit/entry 失败，runtime 仍保留清理根。

binding stage 单向为 `ARMED → BOUNDARY_SPEC → BOUNDARY_OBJECT`。准备 B_S 时核 exact source CodeType/defaults 与原 binding proof，再保存 close spec/proof；实际 boundary 在 `claim_pending` 前绑定，并强持有原 state member descriptor。每次绑定重新封存 cleanup roots；重复、逆序与根替换拒绝。execution state 为 `IDLE → RUNNING → CLOSED|UNRESOLVED`；失败重复调用返回同一 carrier，不重复 HANDLE close。

收尾按 runtime bookend、B_S、namespace、native 顺序；各域独立保留 secondary。非 Native packet 根漂移阻止域代码执行，仍从 owner anchor 独立核并收尾原 Native 资源；原 native 根、ownership 或 LIVE 句柄真值漂移才拒绝相应 leaf。B_S 与 namespace 使用原 CodeType、原 context 和固定 verifier proof。proof 失败时，B_S 只经原 state slot 将状态仍可达的原边界置为 FAULTED/inactive；namespace 只从原 modules 中删除仍指向原 module 的 alias。foreign alias（包括 None）、foreign container 和畸形 B_S state 保留并记录 unresolved。

native 使用与 Core44 AST 相同的 `_Resource.close` CodeType，在共享原 pending/close_calls/guard/early 的 capsule 上执行；view 初始 phase 有值，原 resource phase 写回。原句柄顺序仍为 thread、process；close witness 不确定保留 `close_issued`，后续调用不重试数字句柄。终态核共享容器身份、两次 close 账、pending、phase、hooks 和原 API/metadata。旧 hooks 的停用与 terminal publication 独立处理；carrier 使用预持有的低层异常构造方法，保留 primary 和全部 secondary。

## 验收矩阵

| 范围 | 测试方法 |
|---|---|
| compiled-source oracle、pre-open capture、LIVE returns、共享账与顺序 | 01–03 |
| owner commitment 前后失败 | 04–05 |
| prepared/unbound、claim failure、B_S proof/异常/foreign/malformed | 06–11 |
| namespace 原 alias、foreign None/object/container | 12–14 |
| native instance/API roots、coordinated pending、LIVE seal | 15–18 |
| 两个 HANDLE 的 close/witness failure、primary/secondary 顺序 | 19–21 |
| swallowed reentry、packet roots、残留 RUNNING、class dispatch | 22–25 |
| native failure class、不可删除字段、控制异常、重复绑定、metadata/publication | 26–32 |

测试执行精确 Core45 constructor/open/transfer/prepare/claim/close/orchestration；kernel leaf、snapshot、entry/bookend、namespace lifecycle 和 B_S lifecycle 明确为合成替身。两个 proof verifier 从实际 Namespace4/B_S4 仅提取函数源码，并以固定默认值执行。Core44/Namespace4/B_S4 bytes 是静态来源输入，不执行其成功 target 路径。32 方法及方法内有限反例每包一次。

## 证据边界

这不是 arbitrary Python/native mutation 的安全隔离。原 context 经 proof 后调用仍存在 check/use 窗口；跨线程、完整传递依赖图与真实 Native 清理等价仍 OPEN。anchor ledger 是受 creating owner 控制的进程内对象；对 anchor/ledger/owner seal 全部协调篡改不提供安全隔离。晚绑定更新 anchor 与 owner runtime seal 之间的异步异常窗口尚未证明原子性。未连接 role v2 的实际 bind/launch effect，未授予 entry/argv/channel、external full context、Guard2/Permission2、P1/source physical-read reuse 或完整 F 的权限。真实 Native/P1/Source49 target 调用为零；普通验证的 Capture1/DRAIN1 自身 Native sampler 与 runner HANDLE 仍如实执行。新增模拟跨度 0h；所有原 science/run/resource/formal/adopted gates 为 false。

独立复核的 findings 仅为 PRE_SEAL；测试数、合成成功、源代码 AST 相同都不能替代真实 owner/OS 状态、两层 quiet 或整链资源审查。
