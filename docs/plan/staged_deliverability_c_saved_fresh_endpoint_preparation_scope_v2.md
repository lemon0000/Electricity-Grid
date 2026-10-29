# F：endpoint/Core 接线普通验证 scope v2

2026-10-30，DRAFT_NONAUTHORITATIVE，依 [设计v2](staged_deliverability_c_saved_fresh_endpoint_preparation_design_v2.md)。v1首次拒绝已checkpoint，全部源码/输入/失败/实际费用保留；本包为独立后继。

validation_methods = 99; endpoint_methods = 30; cleanup_methods = 32; role_methods = 26; integration_methods = 11

唯一账源v1 CP：14340B / `629a459c8405d7836812b752121b59ad7c4f5a6f1fe4a8799a9c66c83c9ee9e8`。accepted/accounting_complete=true、diagnostic_accepted=false；root5/988785B。register1.5128677999964566s、inspect2.796233500004746s、unit9.20010330000514s、checkpoint0.6601587999975891s，包14.169363400003931秒。99方法、5error/1failure、原始log与trace保留；不退款。

累计static710.1496843000234、pytest366.48897970000326、unittest424.10366079998494，总1500.7423248000116秒，59条不接受记录。input1542 + root5 − driver overlap1 = **1546/87400560B**；archive320+5 = **325/40727198B**。own21-overlap13，exact union **1554**；42项snapshot、NFC12原16、Source49、原WIP/B1–B3/P2七输入及历史继承完整保留。

唯一register→inspect→99 unittest→独立PRE_SEAL→saved→checkpoint；首次register冻结own；首拒后仅checkpoint。沿用独立包static34/unit35/总69秒与阶段6/10/35/6/6/6，root10files/4MiB、record1MiB、checkpoint预留1MiB/1slot、测试文本128KiB。真实编译容量重新计算，原raw/XZ/UTF16帽不变。使用同进程synthetic叶函数，不spawn测试子进程，不调用Capture1/DRAIN1、Native sampler或目标Native。

接受范围仅 `endpoint_core_ownership_synthetic_and_transport_only`。99方法通过不能替代真实Native、cold startup、Source49/P1执行、完整角色、连续RSS/整链性能或运行授权。所有相应gate保持false，原F预算、完整输入和科学阈值不变，NFC12不重跑。
