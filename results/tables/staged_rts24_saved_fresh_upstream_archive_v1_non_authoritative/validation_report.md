# 上游合同 archive successor 机械验证记录

2026-10-25，DRAFT_NONAUTHORITATIVE。见[范围预算](../../../docs/plan/staged_deliverability_c_saved_fresh_upstream_archive_scope_budget_v1.md)与[交接](../../../docs/plan/continuation_handoff_20261025_saved_fresh_upstream_archive.md)。起始HEAD/origin `d458c35cfe6b537853d3ff7aee3314f4fd5d5147`。本轮仅机械保存，保持唯一writer/独立只读PRE_SEAL，无seal或运行权限。

本轮固定四导航的双LF标题段，保持完整旧body suffix。独立successor checker重做冻结31-file main、两epoch8份helper snapshots、4设计JSON/21负例、Source49、4105历史路径及旧6条记录；saved_05与terminal_06仍为唯一两个失败。它只动态执行已hash固定的design/direct-entry原stdlib oracle，让原archive在真实当前导航返回；不调用旧失败terminal的verify，也不import当前ENTRY或科学helper。完整复核还需原282/8/P1全683证据，新增pytest/probe/模拟小时均0。

check_01已终态exit0、stderr空，capture charge14.1992600s；它实际返回full_ancestor_archive_verified=true，当前Source49/四导航whole-pin一致，4105路径、P1全683与冻结282/8复核成功。首次draft检查的support/body标志false如实保留。随后保存与终态以saved_02/terminal_03原记录及root checkpoint_status.json为准，本页在support冻结前写入此次实际观测后保持。旧root报告/交接/root checkpoint及failed package原字节不改，旧两个失败仍是exit1/accepted=false。

新预算max4次/120s，每次target≤25s、capture charge≤30s；3计划+1可选同字节成功后重读，失败照计。charge=最初monotonic到post-pin/log-window+0.5s未实测tail reserve，Python最初启动/交互/review/Git不在计量，不能代表研究整链wall/RSS准入。新checks≤24files/4MiB、三文档≤1MiB、终态JSON≤64KiB。所有helpers/snapshots/pins和raw logs保留，support不自pin；尚未写出的自身exit由后继及Git逐blob核。

actual F、科学采用、资源准入、正式结果、生产data validator/bootstrap/issuer/owner/full runtime均未开放。10域/59节点/21项只为旧静态设计证据；26个runtime fault仍UNRUN。
