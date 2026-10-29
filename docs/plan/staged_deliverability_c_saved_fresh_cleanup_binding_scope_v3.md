# F：cleanup binding 普通验证 scope v3

2026-10-30，DRAFT_NONAUTHORITATIVE，依[设计 v3](staged_deliverability_c_saved_fresh_cleanup_binding_design_v3.md)。root唯一writer、独立只读PRE_SEAL。

validation_methods = 69; integration_methods = 11; canonical_frames = 140

唯一账源v2 CP：9978B / `b71b4825805a8d4ea5114881c8d238ae22db487e904a246b99104461ba81d4bb`。accepted/accounting_complete=true、diagnostic_accepted=false；root4/895843B。v2 register2.16081039999699、unit17.064832999996725、checkpoint1.3013839000050211，包20.527027299998736秒；69方法、140帧、1failure/5error原始输出全部保留，不退款。

累计static672.7981306000322、pytest366.48897970000326、unittest377.9662519999765，总1417.253362300012秒；56条不接受记录完整继承。1487 inputs+root4-driver1＝**1490 /81978247B**；archive296+4＝**300 /36075792B**。own13与继承overlap5，精确union **1498**。原WIP、B1–B3、P2七输入、Source49 epoch、NFC12原16files、42项并行snapshot及v1/v2失败历史保持。

唯一流程 `register → 69方法unittest → independent PRE_SEAL → saved raw replay → checkpoint`。三组32/26/11、140frames；48个expression-before/call-after故障场景在register固定完整marker/原CALL/span。AST计数、design/scope ASCII计数行和原F合同静态提取同时核验；每阶段核完整input/archive/own maps与known/charged pins。首次register后own冻结；首拒绝后只保全checkpoint，后继单独登记，无自动重试。

本包独立预算static25、unit30、总55秒；阶段register5/unit30/PRE_SEAL5/saved5/checkpoint5，child25秒。stdout128KiB/stderr32KiB，process256MiB/pair512MiB；root10files/4MiB、record1MiB、checkpoint预留1MiB/1slot。所有阶段与child用`-B -s -S`。普通validation child至多1，Capture1/DRAIN1实际Native sampler/HANDLE清理如实保存；project/fixture child0，项目Native/P1/Source49/solver/完整F/NFC12均不调用。

只接受 `stable_cleanup_binding_and_core_role_join_synthetic_domains_only`，各run/science/resource/formal/actual_F gate不变。真实Native/authority/整F性能与连续资源界仍OPEN。原完整F180秒、19metrics、17targets、12500/6500读取帽及所有科学阈值保持。
