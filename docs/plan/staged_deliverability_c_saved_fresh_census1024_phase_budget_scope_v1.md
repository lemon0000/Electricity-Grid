# 1024后继的完整控制器预算草稿

2026-10-28，DRAFT_NONAUTHORITATIVE，起点bae0a39c4a2c70c5aee2c3798aac124bd415b31b；NFC5实现已形成draft，尚未登记或执行。依据[NFC4完整unit与预算拒绝](continuation_handoff_20261028_saved_fresh_census1024_unit_terminal_v1.md)。本文件固定首次执行前合同；后续状态以对应checkpoint为准，不修改任何已执行包、gate、失败或运行权限。

目标为唯一真实1024个guard-passed open或其前自然返回的完整诊断终态，随后saved与checkpoint重开核验。NFC4旧30s包花费12.96942539999145s后停止，全部7文件726621B冻结；不得重跑、延长原帽或挪用其余量。当前累计792.7747780000602s、不接受36条；旧archive37文件2860142B仍需精确保全。

预算须覆盖每次full current check；不能只按legacy leaf的0.56–0.71s估算。NFC4 register1.2998s、unit7.2134s（runner1.983s，含四check及收尾）、pre_seal首次check加拒绝记录1.4894s、checkpoint1.4026s，是当前代表性证据；新成功路径的startup/profile/actual1024/saved完整开销仍有不确定性。每个完整check保留冻结v3 leaf内部的全部fresh观察点；后继不得增加递归历史checker。pin-memo因不稳定收益和约39.6MB raw占用继续不接入，不追加该局部基准。

拟定独立分配：size≤3 → register≤3 → 唯一完整unit≤10 → PRE_SEAL≤4 → startup≤5 → profile≤4 → 唯一actual1024/return≤10 → saved≤4 → checkpoint≤3秒；static≤36、unit≤10、总≤46秒。所有阶段帽相加等于整包帽；最坏累计838.7747780000602s。固定每check按约1.5s加不确定性核：四check+runner+收尾落unit10s；两check的非cold phase留4s；startup5s与actual10s分别覆盖两check、manifest/transport、实际child和终态清理；checkpoint3s包含一次check、success streams与root回读。这是待绑定实现的预算草稿，不是已测成功全路径或保证。

最多1 unit child及2串行cold child；不得启动model、solver、P1、实际role/Job/F、native校准或长实验。保持窗口1024/最多1023次窗口内physical open、30帧完整unit终态、命令≤30000 UTF16、stdout≤131072B、stderr总≤32768B/census≤24576B、decoded≤131072B。后继root预留16文件/4MiB；执行前须用实际source、command、registration和packed artifacts重核布局，旧archive单独保全。

后继必须建立create-only独立路径、明确本包source与前驱ledger pin，以精确union核输入和完整current注册事实，保留source49和原helper等价性。源码或控制路径有变化时须验证受影响行为，不能直接搬用v4 unit的accepted字段。先做独立PRE_SEAL，核完整DAG/调用倍数、输入freshness、conditional origins、预算和失败保存；这些条件未闭合前不登记或启动。所有费用继续累加，失败不退款，任何拒绝保存原raw/partial及终态后停止，无自动重试或顺延。

具体实现位于results/tables/staged_rts24_saved_fresh_nfc_v5_non_authoritative；driver与import_policy为首次size前两个文件。policy保留冻结NFC4原4745B、SHA 4b731fc38ed2b52bff727acf0b02e4b8da7396cb17f2354225b34348155d9e9c。core32/probe30/parent29、native fixture4与test5由experiments/staged_rts24_saved_fresh_census1024_controller_relocate_v2.py精确构造：迁移root/core/probe路径，test01保留旧oracle并包本层constructor，test07仅将预算fixture更新为36/10/46及越界47；全部14节点和其他断言保留。helper census1024_none_v2及原scientific/source49不改。

前驱ledger为NFC4 checkpoint SHA 774f4978e333bb05b79f6245f86e2e4b6faf4b2d3ff566046712f2dc84be6b4d，明确accepted=false/diagnostic=false、count36；每check重核其7文件原bytes、当前曾执行的345直接输入及已通过unit，不将旧checkpoint改为通过。固定v3 leaf仍逐次完整执行；不调用NFC4 driver.check，不新增递归checker。继承输入精确合并v2/v3的933项与NFC4直接输入为1051，另绑定本包新输入、NFC4 unit/registration pins；原unit只作历史保全，仍必须跑本包唯一14节点完整终态。当前registration按fresh inputs、graph、runtime origins、source、迁移、command、helpers/snapshots及全部控制字段重建，维持精确canonical schema/type比较。

这增加每check对前驱345输入的fresh读取，不能把旧leaf成本当作当前full check。按NFC4实测约1.3–1.5s/check量级并在新阶段留余量；具体执行仍以各原帽为停止条件。Unit有父/子前后四次full check，其他phase前后各两次，checkpoint一次；所有阶段保留同一固定leaf内部约2496次显式Path.read_bytes，另加前驱输入、当前输入与phase artifact回读。最多2串行cold child的成功与昂贵失败分支、packed raw恢复、句柄/管道/readers收尾均在本包caps中，runtime/资源/硬停止的更广权限仍不成立。

本草稿仅用于后继实施与性能准入。当前没有新run authority、production seal、official verdict、完整runtime/科学/资源/正式结论，全部相关gate维持false；宽goal仍active。
