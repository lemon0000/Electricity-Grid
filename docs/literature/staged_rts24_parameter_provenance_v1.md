# RTS-24阶段算例参数来源登记

2026-10-23，DRAFT_NONAUTHORITATIVE / PRE_SEAL_AUDIT。[机器登记](staged_rts24_parameter_provenance_v1.json)、[静态核对合同](../plan/staged_deliverability_parameter_provenance_contract_v1.md)和[保存观察](../../results/tables/staged_rts24_parameter_provenance_v1_non_authoritative/audit_01.json)共同记录当前范围。三份原YAML与运行实现均保持原字节。

登记逐叶覆盖 public 40、business 60、rights 32，共132个配置字段；数组逐元素编号，整数键保留类型。每行记录原值/类型、单位、原始来源类别、公共运行采用方式、直接来源pointer、语义角色、精确变换、经验资格和主张限制。37项输入按既有规则精确乘200；public_value_record表示输入变换，不是逐小时实际轨迹。原始来源类别和运行采用方式分别列出，精确缩放不会改变经验资格。

公共静态case按固定源码SHA提取 baseMVA、bus、gen、branch、gencost 五组字面量及形状/摘要，不执行case函数。该记录是组级benchmark来源登记，不逐个分类公共数组单元。原MVA标注的支路rating数值被既有DC实现当MW限额使用；未提供AC换算或工程容量认证。源码头部的原文引用及BSD式许可声明仅作本机来源记录，本轮没有重新访问外部页面。

原rights.network的17项、small.grid四个标量/临时字段未被公共运行采用。部分旧时点和标量仍用于选定的一致性guard，辅助使用清单未穷尽所有审计数值消费。旧response标签是来源标签；实际事件rule为固定实现guard；RATE_C变化保留在网络身份中，活动DC约束使用RATE_A。前史f固定为0，Y按来源缩放，due=h+2不截在观察终点。early/late仍只表示机制清洁时序。

静态checker绑定13个实现/规则引用，检查12个Python AST的选定字段和导入关系；CLI显式输入19文件、首尾共38次读取。词法见证及源码SHA不能替代执行、完整数据流或环境闭包证明；期望映射重构也不是独立科学oracle。128项普通检查（78新、50相关）通过，保存CLI exit0、0科学构模/solver/native；[验证与审阅](../../results/tables/staged_rts24_parameter_provenance_v1_non_authoritative/validation_report.md)保留发现与修正。

当前三份YAML的逐字段来源可追溯性已补齐。非YAML策略选择未被穷尽登记，现实业务/设备/任务、SLA、权益合同、清洁归属、延期和事故概率仍未经验校准。公共实际g、139静态节点、完整反事实F/X时序、D/E数值方案与留出、C/D/E资源及P1专项授权维持原状态。该登记不产生official verdict、seal或receipt。
