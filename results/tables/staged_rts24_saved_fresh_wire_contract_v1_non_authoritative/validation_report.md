# successor wire、startup 与projection静态合同

2026-10-26，DRAFT_NONAUTHORITATIVE。见[范围预算](../../../docs/plan/staged_deliverability_c_saved_fresh_wire_scope_budget_v1.md)和[当前交接](../../../docs/plan/continuation_handoff_20261026_saved_fresh_wire_contract.md)。完整保存状态以本root checkpoint_status.json和外部原exit为准。

本轮补45个逻辑schema、94节点DAG和cross_field_constraints；生产ENTRY、tests、科学adapter及Source49未改。设计固定完整mailbox kind/sequence/nonce/header绑定、entry原attempt与四slot提交、bootstrap/self proof carrier、原descriptor阶段序列、具名return references、共享failure预算及物理carrier。完整验证/发射器、真实bootstrap/issuer/owner均未实现。

编码上界来自逐字段canonical ASCII JSON求和，包含键和全部标点、嵌套descriptor/receipt、固定argv及Windows command-line保守公式。request最大1763B，七字段envelope354B；最大完整stage header3496B，加44为3540≤4096；startup7248≤16384；failure24242≤32768。controller/parent/fresh projection bundle上界1040/4695/4593B，满足17408值帽与18476物理slot。stage物理mapping为1 header+16 frames；bootstrap/正常phase/terminal完整成功帧分别12/7/3≤16，error/terminal后不再追加。

原design_02实得43个合同结构破坏拒绝及3个synthetic hash relation拒绝。PRE_SEAL之后补三条proof→G0/hold边和逐sequence phase/吸收/容量规则，原reserve_05已终态0/accepted=true，新50结构拒绝及3个hash关系通过。旧设计三JSON与旧helper按实际SHA保存，draft_revision_03绑定两epoch，不把原43项当作后补条件已验证。结构oracle不是production packet validator，36个runtime fault cases均UNRUN。

一个wrapper解析失败的原脚本、原scope和工具decoded combined输出保留；没有target启动或分流raw可供冒称。失败计1.3421054s，成功baseline/design/reserve之后、saved前的静态账9.3848743s。全静态预算仍120s，剩余saved/terminal各≤30，完整终态账见checkpoint；Python启动/编辑/review/Git不属于capture窗口，不据此认定完整workflow或资源准入。

保存检查核4290前序路径、P1全683、未变Source49及旧480冻结节点/三次当前timeout/两次祖先失败。480是复用冻结证据，本轮new executed pytest=0、cold probes=0、模拟小时=0。saved oracle核完整main freeze、helper/设计epochs、文档导航双LF与旧body suffix，再运行pin绑定的前序stdlib archive；它不import当前ENTRY、builder或其他科学实现。自身尚未结束的capture由外部记录和Git逐blob承接。

actual fresh、最终父端采用、整包科学采用、生产闭包及资源/正式门禁均未完成。本轮产物提供下一阶段实现的字段、carrier、因果和预算依据；这些设计数据和JSON标志不能发行permit或证明实际quiet。
