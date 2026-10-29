# F：full-context role 合成机制验证 scope v2

2026-10-29，DRAFT_NONAUTHORITATIVE。接续[scope v1](staged_deliverability_c_saved_fresh_full_context_role_scope_v1.md)冻结失败，通过[设计 v2](staged_deliverability_c_saved_fresh_full_context_role_design_v2.md)只修门禁测试漏传参数。root唯一writer，独立只读PRE_SEAL。普通短时合成测试不授予Native/P1/Source49/完整F权限；不重跑NFC12，新增模拟跨度0h。

## 完整继承与原账

账源 `staged_rts24_saved_fresh_full_context_role_v1_non_authoritative/checkpoint.json`：8880B，SHA `76173a1df7041048f4d9cc0bee39fe90d0dea472335a57fd2e1808672995f401`，accepted/accounting_complete=true、diagnostic_accepted=false。原26方法跑完，1 error的test01是漏传keyword-only outer_deadline；原始stderr/stdout/所有帧和failed unit记录冻结。v1本包11.672237799997674秒；累计static645.926573500022、pytest366.48897970000326、unittest340.97076189996733，总1353.3863150999925秒，53条不接受记录全部保留。

v1 root5文件/844982B；expanded1433＋root5−driver和before_repair overlap2＝1436继承输入。archive271＋root5＝276文件/31872995B。own7：runtime v2、test v2、design v2、scope v2、driver v2、Capture1/DRAIN1；overlap2，精确union1441。v1全部own、原WIP交接/state/48360B原始source snapshot，以及所有历史失败/charged/known pins完整继承。snapshot固定SHA `cdfbad787960572c520955bfa8e1187027a2d83d70cf5308050b965ec20ab838`，单独断言且只读不执行。

register及各阶段核完整集合与exact own pins；首次register后全部own字节冻结。原39项并行dirty保持，B1–B3/原P2七输入/所有冻结失败不变。Source49 epoch `acc4a25f3c1b2e59408a22394504b74223c9887016d42812b9dd1e61115e3875`；NFC12原16文件及CP `bbe4eaf6a67d5025db498bde68526c3fd2352e3a71edf05a21711505067b70de`保持。

## 执行次数、停止与保存

固定 `register → 唯一26方法unittest → independent PRE_SEAL → saved raw replay → checkpoint`；每方法及有限反例循环一次，无自动重试。只有一个 `-B -s -S` 普通capture runner，fixture均为内存数据与函数，0child进程/项目target import/Native owner/P1内容读/角色/模型/solver调用。

阶段帽5/12/5/5/5秒，unit child10秒；static25/unittest15/总40秒。原包余量不退款不转移。Capture1/DRAIN1：stdout128KiB/stderr32KiB、process256MiB/pair512MiB；root10文件/4MiB、record1MiB，checkpoint预留1MiB/1slot。采样RSS不证明完整F连续上界或combined retention。

strict phase prefix/exact inputs/archive/own/closed gates逐阶段核；首个拒绝后只保全checkpoint，原流/错误/已完成物理事实/费用保留，后续修改进入新successor。checkpoint费用纳入static，register失败也不得丢失原账。保存回放核54个canonical帧、26 nodeid/start/end、rc/stdout/stderr pin及quiet/handles/pipes/readers/memory guard；接受范围仅synthetic_full_role_failure_windows_only。独立只读审查不得签official verdict/receipt/seal。真实完整F及外部授权/清理等价/整链预算缺口继续OPEN。
