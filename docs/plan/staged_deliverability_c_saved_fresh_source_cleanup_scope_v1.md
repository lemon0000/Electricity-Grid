# F：Core45 来源清理普通验证 scope v1

2026-10-29，DRAFT_NONAUTHORITATIVE。按 [设计](staged_deliverability_c_saved_fresh_source_cleanup_design_v1.md)验证 Core45 来源创建/交接/cleanup code；root 唯一 writer，独立只读 PRE_SEAL。此次只含静态检查和有限合成单元测试，不启动 Native/P1/Source49 target、solver、角色或完整 F，不重跑 NFC12。

## 完整继承

唯一账源为 role v2 checkpoint：9378B，SHA `a534521c8f8365d82cfe395d85b280a78809a3129cc760f661247f8e852a2f29`；accepted/accounting_complete/diagnostic_accepted=true。累计 static653.3531790000227、pytest366.48897970000326、unittest350.93306609996944，总1370.7752247999954秒。53条不接受记录全部继承，原 role v1 失败及其11.672237799997674秒不退款。

role v2 的1441 inputs＋root6−driver overlap1＝1446继承输入/77829108B；archive276＋root6＝282文件/32676367B。own9 为 Core45、test v1、design/scope v1、driver、Capture1/DRAIN1、role v2 handoff、当前工作区 snapshot；只有 Capture1/DRAIN1 overlap2，精确 union1453。Core44/Namespace4/B_S4 已在继承集合中。首次 register 后所有 own 字节冻结，失败以 create-only checkpoint 保全，修补进入独立 successor。

逐阶段核完整输入与 archive 的精确集合、bytes/SHA、own、历史 known/charged pins。保留原 WIP source 48360B/SHA `cdfbad787960572c520955bfa8e1187027a2d83d70cf5308050b965ec20ab838`。Source49 epoch `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`、NFC12原16文件及CP `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de` 保持，B1–B3、原P2七输入及全部失败工件保持。当前并行工作区以 snapshot 记账，root 不修改摘要、引言、图件及已有 dirty 导航文件。

## 次数、资源与停止

固定 `register → 唯一32方法 unittest → independent PRE_SEAL → saved raw replay → checkpoint`。每方法/有限反例一次，无自动重试。所有外层 driver 阶段及 child 均用 `-B -s -S`，入口强制 dont_write_bytecode=true。project_target_child_processes=0；唯一实际子进程为 ordinary unittest runner，saved/checkpoint 单列 validation_child_processes=1（若尚未运行为0；失败缺少物理见证则unknown）。Source49模块执行/P1内容读/项目target Native HANDLE leaf/solver/模型调用均0。原 Capture1/DRAIN1 仍以实际 Native sampler 观察普通 runner，关闭并核其 HANDLE，这不属于项目 target 运行。源文件库存读取和合成 code 执行不计作真实目标物理 I/O。

register/unittest/PRE_SEAL/saved/checkpoint 阶段帽5/12/5/5/5秒，child10秒；static25、unittest15、总40秒。原包余量不转移。Capture1/DRAIN1原帽：stdout128KiB、stderr32KiB、单进程256MiB/进程对512MiB；root10文件/4MiB、单record1MiB；checkpoint预留1MiB/1slot。采样RSS不证明完整F连续上界或combined retention。

首个拒绝后只保存 checkpoint。原流/每方法帧/错误/已发生效果/费用全部保留，不丢弃预算超限、失败或 cleanup 不确定记录。saved replay核66个canonical帧、32 nodeid/start/end、rc、原 stdout/stderr pin、capture quiet/handles/pipes/readers/memory guard。接受范围仅 `source_specific_cleanup_synthetic_domains_only`，不签 official verdict/receipt/seal，不开放任何原 gate。

真实来源 cleanup 的 check/use/transitive equivalence、actual entry/full context、P1/source costs及whole F DAG预算仍OPEN。任何实际诊断须另备具体包、次数、上限、停止条件和专项运行授权。
