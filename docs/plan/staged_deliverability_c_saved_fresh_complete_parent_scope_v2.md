# F：Parent memory cross-binding 故障夹具后继

2026-10-29，DRAFT_NONAUTHORITATIVE，登记前自身受控费用 0。继承 [v1 完整合同](staged_deliverability_c_saved_fresh_complete_parent_scope_v1.md) 的 source-held Parent40、QuietActor2、complete validator1、23 项矩阵、两次固定 stdlib toy、权限与资源边界。v1 登记后的 production source/test/scope/driver/input/raw 全部冻结保留。本后继仅修改 test10 的数据故障夹具，生产源码不变。

v1 实际 23 项全部执行，22 pass/1 failure/0 error/skip，runner 4.992s、outer 8.910682099987753/12s，48 canonical 帧含完整拒绝 report。rc=1、capture_error=null，stdout 8507B、stderr 7525B，无 kill/truncation/reader/cleanup，handle/pipes/readers 均终态。两个真实微型 child 已通过完整 source_dispatch capture/run/observation；默认 graph/anchor、packet、profile、witness、capture/JSON/cap/retire 前后/foreign registry/失败重开其他用例执行完成。整包没有通过，不能以 22 项代替完整验收。

唯一失败是 test10 的 child_pid 分支只修改 memory guard.binding.child_pid，先被 DRAIN2.validate_guard 的内部 child_pid==drained_child_pid 断言拒绝，未到预期 Parent ValueError。新测试选择与原 parent/child 都不同的正 uint32，child 分支同时修改 binding.child_pid 和 drained_child_pid，让 guard 内部自洽；quiet.kernel_identity.pid 与 direct_child_pid 原值保持，重算 drain_observation_pin。断言进一步收紧为 Parent 的 same live sampled parent/child pair ValueError，证明跨证据绑定实际拒绝。parent_pid 分支同样使用明确不同的值。独立只读复核确认不弱化生产检查。

唯一 23 项仍完整执行一次，不执行旧 70 项或 NFC12。成功 toy 使用 outer 绑定的 private source copy（显式 synthetic graph/anchor/context），两个 child 只读 system temp 合成 payload、固定 stdin release、sleep 0.12s、查询自身 kernel/command 并输出数据；项目 Native owner、Source49 目标、P1 内容、角色、模型、solver 均为 0。startup 递归另用明确纯数据 fixture；所有 positive 仅支持普通实现分支。真实 outer/grant、external profile anchor、两个非 startup exact graph、Parent 683 内容重开及 whole-workflow 资源准入仍 OPEN，所有运行/科学/正式/F gates false。

DAG 与帽全部保持：register → 唯一 unit → 独立 PRE_SEAL → saved 原流 → checkpoint → scoped Git，拒绝后仅保全账；5/12/5/5/5 秒、child 10s、static 25/unit 15/总 40s、ordinary capture 128KiB/32KiB、256MiB/process/512MiB pair、root 10 文件/4MiB、record 1MiB/checkpoint reserve 1MiB。登记后自身字节冻结，不重试原 scope，不扩大预算。

账源固定 v1 CP **d194849e7eca6ce4ddaa0c581e3d47dfdba35e2354f5d5b05ea3b327fc4c1a30**，7627B，root 4 文件 783948B。v1 register 1.0888222999928985s、unit 拒绝 8.910682099987753s、checkpoint 0.5203438000171445s，共 **10.519848199997796/40s**；accepted/accounting_complete=true、diagnostic_accepted=false，仅保全账。累计 static **633.0126498999991s**、pytest **366.48897970000326s**、unittest **320.6123683999649s**，总 **1320.1139979999673s**，**52 条拒绝**。费用不退款、剩余不转用。

继承 effective 1402 加 root 4 扣 driver overlap 1，精确 **1405 inputs**；archive **259/29406028B**。own 5 为 test2、scope2、driver2、Capture1、DRAIN1，重叠 2，effective **1408**。完整 input/archive/known/charged 及历史失败逐 pin；Source49/NFC12 全 16 文件、原 39 项并行字节、B1–B3、原 P2 七输入保持。root 唯一 writer，retained_lifecycle_review 仅 non-authoritative PRE_SEAL，无 official verdict/receipt/seal。
