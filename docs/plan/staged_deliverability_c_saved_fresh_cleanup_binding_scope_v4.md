# F：cleanup binding 普通验证 scope v4

2026-10-30，DRAFT_NONAUTHORITATIVE，依[设计v4](staged_deliverability_c_saved_fresh_cleanup_binding_design_v4.md)，root唯一writer、独立只读PRE_SEAL。

validation_methods = 69; integration_methods = 11; canonical_frames = 140

唯一账源v3 CP：9980B / `ed70e42a372535f2a71423d93217f743a0f9dd76bb5e1ebd9ca1137df687e804`，accepted/accounting_complete=true、diagnostic_accepted=false。root4/909851B；register2.587925499996345、unit16.710189800003718、checkpoint1.5179633000007016，包20.816078600000765秒。69方法/140frames/5error，48故障场景通过；所有原始失败与费用保留，不退款。

累计static676.9040194000293、pytest366.48897970000326、unittest394.67644179998024，总1438.0694409000128秒；57条不接受记录保持。1498 inputs+root4-driver1＝**1501 /83119890B**；archive300+4＝**304 /36985643B**。own13-overlap5，exact union **1509**。原WIP、B1–B3、P2七输入、Source49 epoch、NFC12原16文件、并行42项snapshot及全部失败历史完整继承。

唯一 `register → 69方法unittest → independent PRE_SEAL → saved raw replay → checkpoint`；方法32/26/11、原流140frames、固定48场景与五项递归LOAD_GLOBAL集合。AST与文档ASCII计数行、原F合同AST快照、full input/archive/own与known/charged pins每阶段核对。首次register后own冻结；首拒绝后仅checkpoint，无自动重试。

独立包预算static25/unit30/总55秒；阶段5/30/5/5/5，child25秒。stdout128KiB/stderr32KiB，process256MiB/pair512MiB；root10files/4MiB、record1MiB、checkpoint预留1MiB/1slot。五阶段与child均`-B -s -S`。ordinary validation child至多1，实际Capture1/DRAIN1 Native sampler/HANDLE如实保存；project/fixture child0，项目Native/P1/Source49/solver/完整F/NFC12均0。

只接受 `stable_cleanup_binding_and_core_role_join_synthetic_domains_only`，无official verdict/receipt/seal，各run/science/resource/formal/actual_F gate不变。原F180秒、19metrics、17targets、12500/6500读帽与全部科学阈值保持；真实入口/Native等价/整体F与连续资源界仍OPEN。
