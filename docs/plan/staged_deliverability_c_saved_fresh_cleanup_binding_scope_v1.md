# F：Core47 与 role cleanup 接线普通验证 scope v1

2026-10-30，DRAFT_NONAUTHORITATIVE。按[设计](staged_deliverability_c_saved_fresh_cleanup_binding_design_v1.md)验证固定 anchor 与 source cleanup join。root 唯一 writer，独立只读 PRE_SEAL；项目 Native/P1/Source49 target、solver、完整F、NFC12 调用均0。Capture1/DRAIN1 实际普通 runner Native 采样/HANDLE 清理如实计入；validation child 至多1。

唯一前序账源 source_cleanup_v2 checkpoint：10195B / `ddcee35a4b0540f415c45279d00082660040503136935f9af5a62bd2d8e50423`，accepted/accounting_complete/diagnostic_accepted=true。累计 static665.5003612000321、pytest366.48897970000326、unittest358.6759654999769，总1390.6653064000122秒；54条不接受记录、两个 source-cleanup 包19.890081600016856秒及全部历史费用不退款。

继承原1461 inputs加最新root6减driver overlap1，先得到 **1466 /79771677B**；archive **292 /34343363B**。之后与实际 own 精确 union。driver 核完整 predecessor input/archive/own maps 与 root6/831576B、old known/charged pins。B1–B3、原P2七输入、原WIP、Source49 epoch与NFC12原16文件均完整继承，旧失败及历史不重写。42项并行工作区沿用 source_cleanup_state_v1 snapshot。

唯一普通路线 `register → 68方法unittest → independent PRE_SEAL → saved raw replay → checkpoint`。原 Core32与role26加关联10个方法；fault points 在register由AST/实际CodeType固定，不在观察结果后扩充。registration同时保存原F合同AST快照和两项条件P1算式。首次register后own字节冻结；首个拒绝后只允许保全checkpoint，修复进入独立successor。

本新包独立预算 **static25 / unittest30 / 总55秒**，无既有包余量转入；阶段帽 **register5、unit30、PRE_SEAL5、saved5、checkpoint5**，child25秒。stdout128KiB/stderr32KiB，process256MiB/pair512MiB；root10文件/4MiB，单record1MiB，checkpoint预留1MiB/1slot。五阶段与child使用 `-B -s -S`，driver禁止optimized与bytecode。方法及有限fault matrix各包一次，无自动重试。

saved核140 canonical frames、68唯一nodeids及顺序、report/rc/raw SHA、capture HANDLE/pipes/readers/quiet/memory observations。只接受 `stable_cleanup_binding_and_core_role_join_synthetic_domains_only`，不授予真实Native/entry/full-F权限、连续资源上界或combined retention。原完整F 180s、19 metrics、17 targets、12500/6500帧帽及所有科学/运行门禁保持。PRE_SEAL无official verdict/receipt/production seal。
