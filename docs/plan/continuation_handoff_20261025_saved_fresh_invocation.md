# C：F 外部调用能力开发交接

2026-10-25，DRAFT_NONAUTHORITATIVE。接续[角色交接](continuation_handoff_20261025_saved_fresh_roles.md)，起始HEAD `e83575923318fe09836c09cc164eea722bf2b341`；本轮发布hash以远端读回为准。活动目标“持续推进计划”继续，actual saved F 尚未完成。本轮为 ordinary fixture 开发，没有新增模拟小时、solver/native 求解或正式运行。

ENTRY 已接外部 host→broker→controller→parent→fresh。真实 ready capability 有1.5s standby自过期、creator/thread与kernel PID/creation/image绑定；invoke START前固定绝对时钟。broker Job内独占发布context，host以独立held request核 exact raw context、receipt、root/ancestor身份并ACK；controller只在ACK后构造。ACK SHA绑定descriptor/实际启动输入。十个固定RAM slot具独立方向nonce、单次writer及commit-last；broker terminal另绑连续progress前缀/pins/transcript，缺失尾部必须全零。busy不能证明不存在；取得mutex后的非零坏commit/length/SHA即永久未决。

controller真实驱动原parent/fresh、relay、创建式发布/G0–G3调用/最终库存；两级return均待对应完整quiet/close后才读。outer broker Job含全部后代，host active只做kernel+固定RAM，normal实测禁止source/目录/存在性检查或actor构造。原错对象强持，active monitor错误在stage cleanup返回后直接重抛，后续不消费InvocationMailbox/probe/terminal；close错误secondary。异常内容本身不冻结，bounded error image封在OwnedStage commit中。

ordinary role_graph/invocation的系统conhost仅按GetSystemDirectoryW、唯一retained PID/creation/精确image分类，仍须原完整quiet/close才成功；其他后代失败。最后constructor marker含未accepted slot做只读书挡，资源失败不被marker/bookend覆盖。publication kill遇abandoned保留不可序列化capability及actual process record，不能冒充函数成功返回。

最终epoch127唯一nodeids终态通过：27 protocol/6 graph/6 edges/87 stage及原guard/1 bootstrap；SF49首尾及snapshot一致。全部pytest开发attempt累计220.750s＜240s，静态/collection保存检查另按60s。normal outer stage observation3.063s、arming0.234s；kernel完整嵌套成员8/6/4/2，O为16文件/33,846B。prepare、constructor、publication的20s native wait分别约2.984/3.000/4.625s停止；publication为retained unresolved，另外两wrong ACK在构造前拒绝。两resource case外层primary和stage monitor像一致；quiet未知/expiry/busy均有终态。详见[报告](../../results/tables/staged_rts24_saved_fresh_invocation_v1_non_authoritative/validation_report.md)与[合同](staged_deliverability_c_saved_fresh_invocation_development_contract_v1.md)。

adapter17历史检查仅在47来源/科学src/bootstrap与测试AST不变域复用；本轮早epoch角色unit26以AST及invocation专用guard差异证明复用。均不计当前127，未重跑旧role graph全部10节点。原始失败/早epoch不作最终源码通过证据；31图/205 archive entries从stdout精确派生，context只存原pin和省略environment的projection，不能当原context消费。

恢复先核Git/进程、读本页、原[F范围/预算](staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md)与本轮合同，使用compute Python＋`-B`运行新证据`results/tables/staged_rts24_saved_fresh_invocation_v1_non_authoritative/checks_01/saved_checks.py`。保存检查只核机械完整性/冻结snapshot，不是科学或运行准入。1315旧路径、三导航全部旧body、P1全683与原SF49/17 targets/四记录cap保持。

下一步接通真正saved context的entry/owner分支与`execution_context`身份约束，闭合完整parent→fresh→最终父端路径，先核完整调用清单、context/四record最大合法编码与发布/昂贵失败成本，再判断原一次F的安全与授权条件。ordinary capability不能用于生产schema。原40＋5＋5/180s及一次parent/一次fresh/零solver重试保持；arming自举、host最终分配/发布硬中断、整体资源仍OPEN，不能拿本轮15.3s/8s小帽替代。真实P1五模拟小时fresh未执行，局部saved verified、F_launch_admitted和整包science/resource/formal全false；完整319/139/F-X、C整体和D/E比较/敏感性/留出继续OPEN。没有official verdict、receipt、seal或run authority。
