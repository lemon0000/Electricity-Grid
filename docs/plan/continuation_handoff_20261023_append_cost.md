# C保存输入的append成本观察交接

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL，接续[batch交接](continuation_handoff_20261023_batch.md)。用户选择保留公共网络方向，RTS-24主比较、两母线机制回归保持；目标“推进计划”继续active。

按[新诊断合同](staged_deliverability_c_append_cost_probe_contract_v1.md)完成一次准备和一次测量，未重试。输入复用旧v1三方法h0/h1，原observation_end=5保持。六成功/六失败、十二独立fresh全部按固定DAG结束：准备12/34，measurement186/514，合计198次selective编译/548描述，0 full compiler/构模/native/solver。注册SHA为`aebdd0be608c771b0571622d710b54641804a9173183252fc1424577137b9dd1`。

外部准备12.454271s、测量156.945949s；测量guard outer130.984s，quiet后controller处理23.037932s。实际26个Job成员HANDLE全部signaled，active0/final_pids空。采样tree peak RSS298913792B，core571文件1455342B，完整cost_probe_01为579文件1660401B。controller自身RAM和外部记录另计，不把guard wall/RSS称为全流程值。

三方法v2/v3完整state、typed CAS逐字节、summary/audit、保存重开与baseline一致。unknown不采用候选、fresh确认一条；deletion只删除本case新journal对象，另保留原字节，fresh拒绝；reference未决保留零接受row的attempt。独立后核验核文件集合、逐case角色、外部intent/log/timing、198/548以及旧绑定；见[报告](../../results/tables/staged_rts24_append_cost_v1_non_authoritative/execution_observations_01/validation_report.md)、[verification_v2](../../results/tables/staged_rts24_append_cost_v1_non_authoritative/execution_observations_01/verification_v2.json)和[启动前开发记录](../../results/tables/staged_rts24_append_cost_v1_non_authoritative/development_checks_01/development_checks.json)。46个不同普通检查、首轮失败及wrapper两项Medium修复均保存；PRE_SEAL无剩余High/Medium实现finding，不是official审查。

保留核验/目录/依赖身份仍有明显实测成本：parent组70.605554s、fresh组54.884973s；read_bytes/runtime/inventory为嵌套inclusive观测，不能相加为独立占比。固定顺序单次观察不支持提速比、百分比或优势推断。累计state/key及扫描/科学前缀增长未降阶；公共数值、完整139/F-X时序、长cohort/真实IO失败和C/D/E预算仍OPEN。

B1–B3、旧codec/journals、batch五源、P1十三源及注册字节保持。P1注册SHA仍为`23577e5d79d3284a260decbfe2258a3103252617953452565a9feeffafbd94e2`，p1_01不存在，未获专项授权；公共方向答复不授予native。没有长实验或正式结果。新cost request绑定的runner/observer/test/合同/wrapper五源现在不可改；修复或扩大路径使用独立successor，旧成功/失败与postcheck记录全部保留。

续作先读AGENTS.md、agent.md第7–9节、本页、C范围及公共包/P1合同、blocker和介绍索引；刷新Git/进程，复用已闭合记录。可用`compute -B -s .../development_checks_01/postcheck.py --allow-cost-attempt`核历史开发绑定；最终postcheck_v2.verify()为只读原工件函数，CLI会排他创建已存在的verification_v2，不能重跑CLI覆盖。需要再次只读核验时import/runpy后调用verify()并另存独立记录。

下一步将这组实际保存成本纳入公共整链资源表，P1待专项授权；仍可独立设计完整F/X时序与增长后继的最小DAG/计数，但不以解析前缀成本外推公共或192h。根代理唯一writer；本轮提交号以最终远端读回为准。
