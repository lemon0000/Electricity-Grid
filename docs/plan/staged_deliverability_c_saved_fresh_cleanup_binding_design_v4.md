# F：cleanup binding successor v4

2026-10-30，DRAFT_NONAUTHORITATIVE，root唯一writer、独立只读PRE_SEAL。沿用[设计v3](staged_deliverability_c_saved_fresh_cleanup_binding_design_v3.md)的固定anchor、capsule与48个expression-before/call-after场景。

validation_methods = 69; integration_methods = 11; canonical_frames = 140

v3唯一69方法得到64正常、5error；48个故障场景全部通过。5error均在Core binding verifier重建处发生：它实际读取全局dict/type，而role capture/check给了空globals。旧raw、费用和失败全部冻结。本后继Core50与Core47–49字节相同；role6只在两处verifier FunctionType context补`dict`和`type`固定根。其余代码不改。

registration独立递归反汇编并固定五个CodeType及嵌套CodeType的LOAD_GLOBAL集合：LocalRuntimeInputs.close、run_runtime_cleanup、cleanup_root_image、cleanup_binding_snapshot均空；check_bindings恰好为dict/type。这是本次具体依赖修复的静态证据，不是完整Native/外部TCB认证。

69方法仍为Core32、role26、关联11，原流140帧；48场景和每场景journal/mirror/seal/claim见证保持。失败后原Core Native收尾、same-owner capsule、LIVE/RUNNING/OBJECT/IDLE readiness、entry-before-clock与sticky carrier同v3。新路径为Core50、role runtime v6及三份对应测试。

普通验证仍使用显式synthetic kernel/entry/bookend/namespace/B_S/role效果；Capture1/DRAIN1自身Native sampler与validation child单列。项目Native/P1/Source49/solver/完整F/NFC12不调用。原预算、完整继承、失败记录及F合同保持：180秒、19metrics、17targets、12500/6500读帽、四件128KiB；12159/12053是条件P1算式。actual_F/science/resource/formal/run gates全false，新增模拟跨度0h。actual entry、Guard2、channel、launcher/quiet和整体性能仍OPEN。
