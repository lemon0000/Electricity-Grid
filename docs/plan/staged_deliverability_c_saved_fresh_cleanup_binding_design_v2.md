# F：固定 anchor / role cleanup 接线 successor v2

2026-10-30，DRAFT_NONAUTHORITATIVE。root 唯一 writer，独立只读 PRE_SEAL。接续[设计 v1](staged_deliverability_c_saved_fresh_cleanup_binding_design_v1.md)，本文件修正其方法数并记录实际 capsule 检查；原机制、失败历史及完整F科学合同保持。

validation_methods = 69; integration_methods = 11; canonical_frames = 140

Core48 与冻结 Core47 字节相同（98453B / `ea92529f8bf2792367bc961d3464309dd2892afc53ba0ada1f9833c41f49ca20`）；role runtime v4 与冻结 v3 字节相同。新路径测试对应 Core48/role4。固定 anchor、三记录 journal、先 append 再写 mirror、OBJECT 先于 claim、namespace/B_S 与 Native 独立收尾沿用 v1。若 journal 内容丢失了 OBJECT 记录，不能恢复或声称 B_S hook 已退休；明确保留 unresolved，Native finally 的终态独立报告。

role 的 CoreOwnerCleanup 是封闭 process-local capsule，保留同 owner/creator、完整 raw、namespace、固定 anchor、原 close packet/carrier、五个来源函数及 defaults。RoleBinding 保留 capsule 身份。bind 与 entry 核来源根、LIVE/RUNNING、cleanup未开始、无failure、原 root image、合法 OBJECT、全部binding/execution mirrors与IDLE ledger；entry 在 clock 回调之前做此检查。失败路径仍从原 held packet 清理，不因现场函数漂移而丢失原 close CodeType/defaults。六个 effect gate 与 public binding 保持关闭，实际 bootstrap namespace/role authority 未认证。

唯一验证矩阵为 **69 个方法：Core 32 + role 26 + 关联 11**，原流 **140 帧**。关联测试静态固定 SPEC 22 个 opcode 边界、OBJECT 22 个边界（包括实际 claim outer CALL）、append 2 个边界；append矩阵分别在SPEC与OBJECT执行，合计48个定点异常场景。还包括 journal corruption、packet loss、ADOPTED/dirty ledger/journal/mirror拒绝、Core→role cleanup成功、primary carrier、child abort失败，以及bind后source roots漂移在clock/hold/replay之前拒绝且原Native收尾不被压住。

kernel leaf、entry/bookend、namespace/B_S lifecycle及role上下文/效果均为显式合成fixture；actual Core/role cleanup orchestration使用精确后继源码。ordinary Capture1/DRAIN1单列一个validation child及其实际Native sampler/HANDLE清理。项目Native/P1/Source49 target、solver、NFC12调用为0；真实入口/Guard2/channel/launcher/quiet/整体物理I/O和性能准入继续OPEN。新增模拟跨度0h，各run/science/resource/formal/actual_F gate全false。

v1首次register后发现scope/design仍写68/10，而AST与机器登记已为69/11。v1未启动测试或child，在unit阶段保存pre-launch拒绝；四文件root和费用全部冻结。此次只修文档计数与driver登记一致性，使用独立后继路径。driver同时核本文件和scope的机器可读计数行、三组AST方法数、140帧预期，避免再次静默不一致。

原F合同勘误继续使用[restricted AST提取器](../../experiments/staged_rts24_saved_fresh_contract_snapshot_v1.py)：**19 metrics、17 targets、180秒**；`12159`与`12053`均为待证明条件P1读取算式。原12500/6500 read帽、四件128KiB预留、原21点/五小时/130CAS保持。旧误写handoff和v1失败文件不改。
