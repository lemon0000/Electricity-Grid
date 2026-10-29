# F：full-context role 合成机制验证 scope

2026-10-29，DRAFT_NONAUTHORITATIVE。root 唯一 writer；八组验收见[设计](staged_deliverability_c_saved_fresh_full_context_role_design_v1.md)。本包是普通短时开发验证，不启动真实 Native/P1/Source49 目标、角色入口或完整 F，不重跑 NFC12。新增模拟跨度 0h。

## 登记集合和继承

唯一账源为 `staged_rts24_saved_fresh_whole_workflow_cost_v1_non_authoritative/checkpoint.json`，10299B，SHA `0ece179a28a3442e9406d1d3c372ea1e27f1376baf5608c734b41aafefc6a11a`。累计 static643.0030709000232、pytest366.48897970000326、unittest332.2220266999684，共1341.7140772999949秒；52条不接受记录全部保留。

完整继承 expanded1420＋原 root6−driver overlap1＝1425 inputs；archive271文件/31028013B。own10：runtime/test/design/scope/driver、原 WIP 交接和 state、原 WIP source snapshot、Capture1/DRAIN1；与继承 overlap2，union 固定1433。snapshot `before_repair.py` 原始48360B，SHA `cdfbad787960572c520955bfa8e1187027a2d83d70cf5308050b965ec20ab838`，只保存/编译，绝不作为 target 执行。原 WIP/handoff/state、所有旧失败/charged/known pins全部登记，不能只核 Source49/NFC12 子集。

register前实际逐pin核验集合，登记时再次完整核；首次register后所有own字节冻结。原39项并行dirty保持。Source49 epoch `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`；NFC12原16文件/CP SHA `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`保持，B1–B3/原P2七输入与历史冻结字节保持。

## 唯一执行和资源预算

固定顺序 `register → unittest → independent PRE_SEAL → saved raw replay → checkpoint`。26个测试方法各一次；方法内有限反例循环以登记source为准，无自动重试；独立只读审查不运行目标。仅一个普通capture unittest runner，含纯内存 child 对象，0 child 进程，固定 `-B -s -S`。AST副本只能调用固定无import纯内存fixture，登记原source/clone/fixture pin。

阶段帽 register5/unittest12/pre_seal5/saved5/checkpoint5秒，unit child10秒；static25/unittest15/总40秒。余量不退款、不转包。Capture1/DRAIN1固定 stdout128KiB/stderr32KiB、process256MiB/pair512MiB；root10文件/4MiB、record1MiB，checkpoint预留1MiB/1slot。sampled RSS不证明完整 F连续上界或 combined retention。费用从各阶段计时开始，成功/失败均记费，checkpoint费用也在static内。

每阶段核 strict prefix、exact inputs/archive/own pins、原累计账、关闭gates和固定nodeid。首个拒绝后停止正向阶段，仅允许保全checkpoint；异常保留原流/原错/已知pins/已收费阶段，不修改登记字节重试。失败后通过独立versioned successor修补。保存回放核canonical逐node帧、rc、stdout/stderr原字节pin、quiet/handles/pipes/readers/memory guard；登记本包原始 scope 是 synthetic_full_role_failure_windows_only。

本次独立审查仅为 PRE_SEAL findings，不产生 official verdict、review receipt、production seal或run authority。真实 Native 清理图、外部角色来源、P1物理读取、完整性能和资源预算仍需后续实际后继及专项运行授权。
