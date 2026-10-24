# C：F 角色连接与创建式发布开发交接

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[阶段监督交接](continuation_handoff_20261025_saved_fresh_stage_owner.md)，起始HEAD为`dc9a452de0b6cec976eec5e7990c84940e86f46f`。完整F继续按[原范围/预算](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)推进；本轮发布hash以远端读回为准。活动目标“持续推进计划”继续，不能把此普通连接检查点当作F完成。

原ENTRY和测试已连接真实parent／fresh两层Job及输出流程：独立解析fixture两侧重算→parent/fresh payload→内层完整quiet/launcher/独立fresh_parent观察→完整比较与candidate→外层完整quiet/launcher→两层启动/身份/记录/候选核对→15文件核心库存/G2→final observation/readback→G3与16文件末次库存→返回。G0在parent reservation前，G1在fresh quiet后比较前；G0–G3在解析fixture中只验证调用和失败窗口，不是原P1库存实测。

固定RAM relay把真实inner_quiesce和成功close后的inner_terminal写入parent自己的上游channel，controller直接读parent帧；没有代写child channel。fresh阶段从实际一次性reservation开始，source/mapping/constructor/capture计入该窗口。ordinary角色preset为parent7.5s/fresh2.9s，保持此前≤8/≤3 envelope；原stage probe及生产40＋5＋5/180s不变。最外controller没有external channel时仅保存自身outer阶段时刻。

RoleStore冻结writer、context文件与所有目录identity；17个target各自固定cap、唯一writer及一次attempt，总预留5,537,792B＜8MiB，四记录512KiB外另留failure128KiB。JSON pending→fsync→no-overwrite rename→readback及publication receipt/末次identity均检查，失败保留phase/expected SHA/may-have-published。读取child内容前核创建线程真实OwnedStage、独立不可变terminal commit、实际完整witness与record一致、全部HANDLE关闭及完整success record；JSON自报不能授予许可。constructor/close/残余descendant HANDLE及fallback _info未决以不可序列化异常保留实际能力，不能吞成普通失败dict。应用日志保持诊断用途，不捕获解释器/bootstrap OS stdout/stderr。

当前精确源码140个唯一nodeid终态通过：real10（27.515s）、unit26（17.266s）、stage/原guard87（16.265s）、metadata/bootstrap17（34.078s），各组SF49首尾一致。最初31通过/2失败（旧0.8s探针phase触帽）、后real10组合30s硬帽终止均完整保存，不计通过。最后优化同一次quiet库存的重复全局扫描，逐文件双遍bytes/identity与能力书挡保留。所有六次pytest累计180.093s，collection7.281s；本轮普通验证300s总预算保持。详见[报告](../../results/tables/staged_rts24_saved_fresh_roles_v1_non_authoritative/validation_report.md)。

九个完整ordinary场景保存原输出snapshot：normal、fresh_error、mismatch、G0/G1/G2/G3错误、outer launcher损坏、G3后payload漂移。normal的两层kernel witness完整且有16个success targets；G0错误不创建Job，其他拒绝均不产生ordinary成功返回。G3错误或晚发漂移保留已发布final observation但返回false，验证文件存在与最后采用不同。context原字节留在pytest输出，Git仅保存original pin和省略environment的projection；projection不能作为原context消费。四记录/普通payload完整原字节保存。

原science adapter完整字节未改，旧科学parent重放证据仅在该不受影响域复用。actual saved的重建/书挡/比较分支仍受旧execution_context约束，owner与entry目前只允许ordinary schema；生产路径尚未接通。CLI `--help`仍exit1并显式禁用。没有新增原P1五模拟小时fresh、native、公共P2或formal run；两个局部saved_P1 verified、F_launch_admitted、整包science/resource/formal均false。1068旧发布路径、三导航全部旧body、P1全683及SF49范围保持。

下一步直接补齐external trusted invocation：调用方须从context创建前持有可执行总deadline、controller实际owner/argv/identity和exact raw context/SHA；覆盖constructor/kernel阻塞、controller自身与worker合计资源，以及controller最终文件扫描/发布/返回/退出。当前普通root端I/O没有外部停止能力，不能用pytest帽或嵌套worker caps替代。确定外部能力与角色channel/argv的精确交付后，再接通真实saved context的parent/fresh/最终父端路径；固定全链实际调用计数、成功/昂贵失败/发布窗口与四记录最大合法长度oracle，再判断那一次真实F的安全/授权条件。保留一次parent、一次fresh、零native/自动重试、原17 targets与所有G0–G3，不增设自证observer。

恢复先核Git/进程、读本页及[开发合同](staged_deliverability_c_saved_fresh_roles_development_contract_v1.md)，运行新证据`checks_01/saved_checks.py`（compute Python＋`-B`）。保存检查仅为机械完整性，区分冻结snapshot与可迭代canonical draft。原65s余量、十小时增长/昂贵失败、完整319/139/F-X、C整体与D/E现实输入/有限比较/选择/敏感性/留出继续OPEN；没有official verdict、receipt、seal或run authority。
