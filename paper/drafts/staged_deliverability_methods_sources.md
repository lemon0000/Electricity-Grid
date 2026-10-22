# 方法章来源与适用范围核对

更新日期：2026-10-23。对应[方法章草稿](staged_deliverability_methods.md)，状态为 DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT。本文记录正文定义的来源与尚缺证据，不是预注册、实验结果、正式审查结论或运行许可。方法章仍可在独立审阅中修订。

## 1 定义与实现对应

| 正文位置 | 主要依据 | 实现对应及边界 |
|---|---|---|
| §1；§2，式（1）—（4） | [当前研究规则](../../agent.md) §§2—6、8；[A最小规格](../../docs/model_spec/staged_deliverability_minimum_spec_v1.md) §§1—4 | 一个接入点、给定建设与接入计划；业务、设备、电网分别给定。真实投运时点是外生路径，策略只见已揭示状态。最终快慢业务数值路径尚未登记。 |
| §3，式（5）—（9） | A最小规格的设备—任务—取电映射、共享资源与逐批期限 | [业务账本实现](../../src/staged_deliverability_development_v1.py)、[公共因果实现](../../src/staged_rts24_causal_v1.py)、[有效后继](../../src/staged_rts24_causal_v2.py)及[独立核验](../../src/staged_rts24_causal_audit_v2.py)。当前每小时一个聚合同质批次。效率作用于工作偿还；恢复上限将债务除以效率和时段长度。真实接受与简化方法假想账本分别解释。 |
| §4.1，式（10）—（12） | [公共网络开发规格](../../docs/model_spec/staged_deliverability_rts24_development_v1.md)；[因果网络规格](../../docs/model_spec/staged_rts24_causal_development_v1.md) | [公共网络请求](../../src/staged_rts24_development_v1.py)、[实际请求子集](../../src/staged_rts24_reference_queries_v1.py)及[独立数值核验](../../src/staged_rts24_causal_audit_v2.py)。正则项、同小时有界纠正与父点角色均按现有开发定义陈述，不改为严格字典序或跨小时机组模型。 |
| §4.2—4.3，式（13）—（17） | A最小规格；[网络四层规格](../../docs/model_spec/staged_deliverability_network_development_v1.md) | 独立加总承诺是共同服务假设；网侧请求未截断，外部清洁额度独立给定。承诺功率缺口与实际匹配电量缺口并列，不互相替代。 |
| §5，式（18） | A最小规格三种评价；公共因果实现及[有效后继](../../src/staged_rts24_causal_v2.py) | 完整时序用原始请求决定调用/恢复，按自己的接受前缀执行。固定余量方法保存假想恢复，瞬时方法不安排恢复；方法自身条件与完整回放条件是两列。恢复端点来自当前拓扑的零额外削减问题，最终实际点仍独立核验。 |
| §6.1，式（19） | 网络四层规格；公共网络请求 | 完整C健康父点与实际P0健康父点不同。完整静态定义有139个逻辑节点；当前有效实际路径不物化完整合同请求，不能据实际轨迹宣称已完成139节点。 |
| §6.2，式（20）—（23） | A最小规格；[局部必要条件合同](../../docs/plan/staged_deliverability_c_business_necessary_audit_contract_v1.md) | [已冻结算术审计](../../src/staged_rts24_business_necessary_v1.py)与独立原始YAML oracle。反事实等效工作不写入真实任务；未知调用区间不选择真实调用，更不生成网络见证。pass=true只表示 not_ruled_out_by_this_necessary_condition，不进入完整合同的成功合取。式（22）保留旧 whole_X 的三条件，设备活动检查另列，不能改写旧判定。 |
| §6.3 四层 | 网络四层规格；[C调用量协调](../../docs/plan/staged_deliverability_c_workflow_budget_reconciliation_v1.md) | 条件实际轨迹、完整静态网络、一小时必要条件、完整反事实时序分别报告；不存在自动汇总成完整合同通过的规则。 |
| §7 终结与数值核验 | [B3终结规格](../../docs/model_spec/staged_termination_development_v1.md)；[journal开发规格](../../docs/model_spec/staged_rts24_journal_development_v1.md)及[retention-v2规格](../../docs/model_spec/staged_rts24_journal_retention_v2.md)；[journal-v3实现](../../src/staged_rts24_journal_v3.py)；独立数值核验 | 记录发布/严格读回是模拟状态采用条件；发布未知、缺输入、已知拒绝和右删失分别保留。有限浮点数与容差审计不称为严格数学界证书；固定策略失败不称为所有策略不可行。 |
| §8 比较与留出 | agent.md §§5、8、9、14；[项目介绍](project_introduction.md) 的比较与敏感性设计；[D/E字段合同](../../docs/plan/staged_deliverability_de_evidence_fields_contract_v1.md) | 可延期比例、期限和CFE目标已有概念候选；最终轴、水平、范围、计划/容量选择规则和独立留出来源/数量尚未确定。方法章描述待实施设计，不报告选择或留出结果。 |

实现对应表示定义可追溯，不表示公共网络已执行同等范围的验证。正文没有新增文献结论；公共静态网络与服务机制的来源资格仍需分别解释，引用既有文献不能代替数值证据。

## 2 当前证据能支持到哪里

- 公共主方向为RTS-24，两母线保留机制回归。现有三母线保存记录也是开发机制证据，不能换名为RTS-24结果。原“early/late”只改变清洁额度时序，不代表业务快慢达产。
- [公共业务必要条件观察](../../results/tables/staged_rts24_business_necessary_v1_non_authoritative/audit_01/audit.json)覆盖40行局部算术。它没有构建网络、实际轨迹、139节点或反事实任务时序；其通过/失败仅解释为相应必要条件。
- [D/E保存报告投影](../../results/tables/staged_deliverability_evaluation_records_v1_non_authoritative/projection_01/projection.json)的20个三母线保存视图不是20个独立样本；12个业务快慢×工程时点×方法只是未绑定分类槽，不是12个数值计划或已预算运行。公共部分只有40行必要条件，其他三层仍未评价。
- 当前有效公共实际路径的摘要保留 full_contract_requests_materialized=false 与 fx_contract_status=not_evaluated_by_actual_path_step；完整静态和反事实跨时证据仍需相应请求与独立核验。完整F/X时序尚未由局部条件推导出来。
- P1注册的 native_authorized=false，p1_01不存在。公共代表成本及总资源准入仍开放；保存报告的读取用时不能估计公共求解成本。无新的公共轨迹、D/E数值比较、容量选择或holdout访问。
- 当前已在组级明确公共静态网络与业务、设备、接入权益、期限、清洁和响应机制假设的边界；逐配置字段的来源类别、直接来源、缩放链和经验资格尚缺统一登记，见[具体缺口](../../docs/literature/staged_parameter_source_gap_20261023.md)。当前机制设定不是同址观测的公共工作负荷，情景等权不解释为现实延期率或经验违约概率。

## 3 文档交付与核对

首次交付为Markdown方法正文与本页，随后补充[PDF阅读版](staged_deliverability_methods.pdf)。阅读版使用既有方法正文的相同字节：8页、166处数学表达式、23编号公式，完成中文正文顺序、字体、边界检查与逐页视觉核对；生成路径及限制见[排版交接](../../docs/plan/continuation_handoff_20261023_methods_pdf.md)。现有介绍MD/PDF及图版保持原字节。

核对包括公式量纲及定义、与有效实现的对应、相对链接、公式编号与定界、原有绑定源/结果和介绍PDF字节，以及只读领域审阅。审阅记录与文档检查保存在新的非权威记录中；它们不修改B1—B3、既有审计、字段合同或P1注册。
