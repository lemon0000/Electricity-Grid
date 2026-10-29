# F：cleanup binding 普通验证 scope v2

2026-10-30，DRAFT_NONAUTHORITATIVE，依[设计 v2](staged_deliverability_c_saved_fresh_cleanup_binding_design_v2.md)。root 唯一 writer，独立只读 PRE_SEAL；项目Native/P1/Source49/solver/完整F/NFC12均不执行。

validation_methods = 69; integration_methods = 11; canonical_frames = 140

唯一账源 cleanup_binding_v1 CP：9978B / `fe33e8f2fd4ee6af039eac5d5116786fbcbbc6e1f4fd52058128a5aee242825c`，accepted/accounting_complete=true，diagnostic_accepted=false。v1 root4/836586B；register2.4277176999967196秒，unit pre-launch拒绝2.2254535000029136秒，checkpoint1.407857400001376秒，包合计6.061028600001009秒，无退款。测试0、child launch attempt=false；v1 checkpoint通用child观察字段为null，unit原始拒绝记录明确validation child=0，不能把null伪装为Native见证。

累计 static669.3359363000302、pytest366.48897970000326、unittest360.9014189999798，总1396.7263350000133秒，**55条不接受记录**完整保留。继承1476 inputs+root4-driver1＝**1479 /80853137B**；archive292+4＝**296 /35179949B**。actual own13与继承overlap5，精确union **1487**。原WIP、B1–B3、P2七输入、Source49 epoch、NFC12原16文件及42项并行snapshot均完整继承。

唯一路线 `register → 69方法unittest → independent PRE_SEAL → saved raw replay → checkpoint`，三组32/26/11，保存140个canonical frame与69个nodeid顺序。register核AST方法数、design/scope计数行和原F合同AST快照；前后全量input/archive/own pins。首次register后own冻结；首次拒绝后只保全checkpoint，不自动重试。

新包独立预算 **static25 / unittest30 / 总55秒**；阶段帽register5、unit30、PRE_SEAL5、saved5、checkpoint5，child25秒。stdout128KiB/stderr32KiB，process256MiB/pair512MiB；root10文件/4MiB、record1MiB、checkpoint预留1MiB/1slot。五阶段和child均`-B -s -S`。ordinary validation child至多1，其Capture1/DRAIN1实际Native sampler/HANDLE收尾如实保存；project/fixture child为0。

只接受 `stable_cleanup_binding_and_core_role_join_synthetic_domains_only`。采样不证明连续资源上界或combined retention；PRE_SEAL无official verdict/receipt/seal，不打开实际Native/F/science/resource/formal权限。完整F的180秒、19metrics、17targets、12500/6500读取帽及全部科学不变量保持。
