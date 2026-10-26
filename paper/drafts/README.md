# 项目介绍与论文草稿

2026-10-26 三角色data-only入口开发验证：见[当前交接](../../docs/plan/continuation_handoff_20261025_saved_fresh_role_data.md)。当前Source版本480目标节点通过（旧282+新198），pytest计费含一次组超时；三次当前失败与旧失败均保存。最终保存状态以新root checkpoint/原exit为准。独立basis仅支持声明与pin一致性；actual fresh、最终父端采用、整包科学采用、资源和正式门禁仍未开放。

2026-10-25 上游合同mechanical archive successor：见[当前交接](../../docs/plan/continuation_handoff_20261025_saved_fresh_upstream_archive.md)。本轮修复双LF标题段并独立重做保存审计；终态以新root原exit/checkpoint为准。旧两次失败原样保留，Source49与10域/59节点/21项静态设计不改，actual F及科学、资源、正式门禁仍关闭。

2026-10-25 successor三角色上游数据合同（DRAFT_NONAUTHORITATIVE）。

执行状态见[最新交接](../../docs/plan/continuation_handoff_20261025_saved_fresh_upstream_contract.md)与[范围预算](../../docs/plan/staged_deliverability_c_saved_fresh_upstream_contract_scope_budget_v1.md)。固定10域/59节点及三角色argv，静态预算≤6次/90s；生产validator、真实bootstrap/actual F及科学、资源、正式门禁仍OPEN。正文贡献与科学结论保持原口径。


更新日期：2026-10-23。

- **给老师阅读的中文项目介绍**：[PDF](project_introduction.pdf) · [可编辑正文](project_introduction.md)。第2节先综述现有工作，再集中总结不足并引出本研究；第3节为本文拟作的三项贡献，第4节解释研究对象与概念，随后展开方法、比较设计及预期交付。
- **英文项目介绍**：[PDF](project_introduction_en.pdf) · [可编辑正文](project_introduction_en.md)。与中文采用相同的研究范围、方法和26条参考文献。
- **方法章草稿**：[PDF阅读版](staged_deliverability_methods.pdf) · [可编辑正文](staged_deliverability_methods.md) · [来源与适用范围核对](staged_deliverability_methods_sources.md)。整理三条进度、任务与功耗、三种评价、网络四层及连续终结；8页阅读版含23个编号公式，数值比较与留出仍待实施。
- **科研卡通图解**：[整体研究框架](../figures/project_framework_cn.svg) · [任务延期与补做](../figures/project_recovery_cn.svg) · [进度错位](../figures/project_rampup_cn.svg) · [实际取电与CFE核查](../figures/project_network_cn.svg)。整体框架连接给定输入、三种评价、阶段判断与独立留出，三张局部图以物件引线标注、箭头含义和编号步骤，分别解释延期与补做、进度错位、实际取电与两类核查；图下逐步说明条件与结局。各图有中英文SVG、PDF及PNG预览；介绍PDF为整体框架单设横向页面。[绘图说明与生成提示词](../figures/project_schematics.json) · [图版组装脚本](../figures/assemble_project_cartoons.py)。
- **引用核查**：[正文编号与文献库映射](../../docs/literature/introduction_reference_map_20261022.csv) · [来源核对记录](../../docs/literature/introduction_source_checks_20261022.json) · [核心文献库](../../docs/literature/literature_matrix.csv) · [建设专题证据表](../../docs/literature/construction_evidence_20261021.csv)。
- **研究执行状态**：[科研执行步骤](../../docs/plan/科研项目执行步骤.md) · [blocker登记](../../docs/model_spec/blocker_register.md)。

项目介绍面向导师，集中说明研究设计与预期成果；方法章按既有定义展开。执行状态、开发证据和历史结果分别在研究记录中维护。
